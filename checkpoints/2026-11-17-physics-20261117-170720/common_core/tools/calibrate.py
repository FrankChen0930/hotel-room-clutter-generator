"""Bounded geometry-only calibration; no render, dynamics or threshold changes."""
import argparse
from pathlib import Path
import json
import math
import sys
import time
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.adapters import area
from common_core.room import load_inputs,prepare_room
from common_core.planner import plan_requests
from common_core.placer import place_requests
from common_core.identity import content_digest
from common_core.manifest import write_json_new
from common_core.paths import guard_new_output
from common_core.metrics import placement_metrics,check_targets


def metrics(objects,room):
    denominator=sum(area(s['allowed_region']) for s in room.supports.values())
    union_area=sum(area(obj['footprint']) for obj in objects)
    points=[[(obj['expected_bounds'][0][j]+obj['expected_bounds'][1][j])/2 for j in range(2)] for obj in objects]
    allpoints=[p for s in room.supports.values() for p in s['allowed_region']]
    diagonal=math.hypot(*(max(p[j] for p in allpoints)-min(p[j] for p in allpoints) for j in range(2)))
    centroid=[sum(p[j] for p in points)/len(points) for j in range(2)] if points else [0.,0.]
    spread=math.sqrt(sum(sum((p[j]-centroid[j])**2 for j in range(2)) for p in points)/len(points))/diagonal if points and diagonal else 0.
    return dict(count=len(objects),coverage=union_area/denominator,denominator_m2=denominator,
                occupied_supports=len({o['effective']['support_id'] for o in objects}),normalized_centroid_spread=spread,
                method='v1 exact polygon area sum on disjoint conservative footprints per fixed allowed support; no stacked placement')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=guard_new_output(args.output);out.mkdir(parents=True);cases=[]
    for room_id in ['hotel705','yazhi']:
        inputs=load_inputs(CODE/'config/deployment.local.json',room_id);room=prepare_room(inputs.profile,inputs.bindings)
        for scenario in ['STAYOVER','CHECKOUT']:
            for seed in [7001,7002,7003]:
                for level in ['low','medium','high']:
                    start=time.monotonic();plan=plan_requests(inputs,seed,scenario,level);placed=place_requests(plan,room,inputs.catalog)
                    record=dict(room=room_id,scenario=scenario,seed=seed,level=level,status=placed['status'],targets=plan['targets'],
                        achieved=placement_metrics(placed['objects'],room,inputs.catalog),elapsed_s=time.monotonic()-start,
                        samples=sum(x['samples'] for x in placed['sampling']),failure=placed['failure'],
                        profile_hash=content_digest(inputs.profile),catalog_hash=content_digest(inputs.catalog),policy_hash=content_digest(inputs.policy))
                    if placed['status']=='PASS':
                        hard_errors=check_targets(record['achieved'],plan['targets'],inputs.policy,room_id,scenario,level,content_digest(inputs.profile),content_digest(inputs.catalog))
                        if hard_errors:record.update(status='FAIL',failure=dict(reason='FROZEN_METRIC_TARGETS',errors=hard_errors))
                    cases.append(record);print(json.dumps({k:record[k] for k in ['room','scenario','seed','level','status','achieved']}),flush=True)
    means=[]
    for room_id in ['hotel705','yazhi']:
        for scenario in ['STAYOVER','CHECKOUT']:
            coverage=[sum(c['achieved']['coverage'] for c in cases if c['room']==room_id and c['scenario']==scenario and c['level']==level)/3 for level in ['low','medium','high']]
            means.append(dict(room=room_id,scenario=scenario,coverage=coverage,strictly_increasing=coverage[0]<coverage[1]<coverage[2]))
    report=dict(execution='EXECUTED',outcome='PASS' if all(c['status']=='PASS' for c in cases) and all(m['strictly_increasing'] for m in means) else 'FAIL',
                variant='baseline',case_budget=36,cases=cases,means=means,scope='geometry-only calibration; policy remains unfrozen until WU-10 after S0 integration')
    write_json_new(out/'calibration.json',report);raise SystemExit(0 if report['outcome']=='PASS' else 5)
