"""Freeze V1 masks/targets from fixed calibration data, before final36 seeds."""
import argparse
import json
import math
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.contracts import load_json,validate_contract
from common_core.identity import content_digest,sha256_file
from common_core.metrics import VERSION


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--calibration',type=Path,required=True);args=parser.parse_args()
    config=CODE/'config';calibration=load_json(args.calibration);policy=load_json(config/'policy.json')
    if policy.get('release_frozen'):raise ValueError('POLICY_ALREADY_FROZEN')
    if calibration['outcome']!='PASS' or len(calibration['cases'])!=36:raise ValueError('CALIBRATION_NOT_ACCEPTED')
    if {c['seed'] for c in calibration['cases']}!={7001,7002,7003}:raise ValueError('CALIBRATION_SEEDS')
    cameras=load_json(config/'cameras/hotel705.json')
    cameras.update(minibar=dict(eye=[.05,-4.22,1.65],target=[-.88,-3.30,.89],focal=23.),
                   entry_bench=dict(eye=[0,-.61,1.65],target=[-.84,-.61,.47],focal=21.))
    (config/'cameras/hotel705.json').write_text(json.dumps(cameras,indent=2),encoding='utf-8')
    cameras=load_json(config/'cameras/yazhi.json')
    cameras.update(cabinet=dict(eye=[.885,5.62,1.63],target=[.235,5.27,.605],focal=24.),
                   bench=dict(eye=[2.55,6.3,1.65],target=[3.4475,6.3,.45],focal=18.))
    (config/'cameras/yazhi.json').write_text(json.dumps(cameras,indent=2),encoding='utf-8')
    catalog=load_json(config/'catalog.json');rooms={}
    for room in ['hotel705','yazhi']:
        profile=load_json(config/f'rooms/{room}.json');camera_map=load_json(config/f'cameras/{room}.json')
        profile['cameras']=[dict(camera_id=key,purpose='FIXED_VISUAL_ACCEPTANCE',**value) for key,value in camera_map.items()]
        profile['profile_version']='1.1-fixed-review-cameras';validate_contract(profile,'RoomProfile')
        (config/f'rooms/{room}.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
        rows=[c for c in calibration['cases'] if c['room']==room];denominators={c['achieved']['denominator_m2'] for c in rows}
        if len(denominators)!=1:raise ValueError('CALIBRATION_DENOMINATOR_CHANGED')
        coverage={}
        for scenario in ['STAYOVER','CHECKOUT']:
            coverage[scenario]={}
            for level in ['low','medium','high']:
                values=[c['achieved']['coverage'] for c in rows if c['scenario']==scenario and c['level']==level]
                coverage[scenario][level]=[math.floor(min(values)*.8*1000)/1000,math.ceil(max(values)*1.2*1000)/1000]
        rooms[room]=dict(profile_hash=content_digest(profile),denominator_m2=next(iter(denominators)),coverage=coverage)
    for minimum,level in enumerate(['low','medium','high'],start=1):
        policy['levels'][level]['spread']=dict(hard=True,occupied_support_min=minimum)
        policy['levels'][level]['coverage']=dict(hard=True,source='metrics.rooms[room].coverage[scenario][level]')
    policy.update(version='1.0-release-frozen',release_frozen=True,
        metrics=dict(version=VERSION,catalog_hash=content_digest(catalog),rooms=rooms,
            calibration=dict(seeds=[7001,7002,7003],source_sha256=sha256_file(args.calibration),
                envelope_margin_fraction=.2,rounding=.001,final_seed_data_used=False,
                rationale='20 percent calibration-only margin; original count ranges and all safety gates unchanged; fixed masks across levels.')))
    validate_contract(policy,'Policy');(config/'policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8')
    (config/'calibration_v1.json').write_text(json.dumps(calibration,indent=2),encoding='utf-8')
    print(json.dumps(dict(release_frozen=True,policy_hash=content_digest(policy),coverage=rooms)))
