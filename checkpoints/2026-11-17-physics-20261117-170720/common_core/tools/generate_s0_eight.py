"""Eight dedicated state/support fixtures, separate from the formal 36 cases."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.contracts import load_json,validate_contract
from common_core.identity import sha256_file
from common_core.manifest import build_manifest,seal_manifest,write_json_new
from common_core.paths import guard_new_output
from common_core.planner import plan_requests
from common_core.placer import place_requests
from common_core.replay import replay_manifest
from common_core.room import Inputs,load_inputs,prepare_room
from common_core.validation import validate_static,validate_integrity
from common_core.writer import write_scene


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=guard_new_output(args.output);out.mkdir(parents=True);records=[]
    for room_id in ['hotel705','yazhi']:
        base=load_inputs(CODE/'config/deployment.local.json',room_id);room=prepare_room(base.profile,base.bindings)
        supports=['bench','desk'] if room_id=='hotel705' else ['round_table','cabinet']
        for state in ['folded','loose']:
            for index,scenario in enumerate(['STAYOVER','CHECKOUT']):
                name=room_id+'_'+state+'_'+scenario.lower();run=out/name;run.mkdir()
                policy=deepcopy(base.policy);policy['policy_id']='S0_DEDICATED_FIXTURE';policy['version']='1.0';policy['release_frozen']=False
                policy['assumptions'].append('Dedicated one-object S0 fixture; not a formal36 Level/count case.')
                for scenario_cfg in policy['scenarios'].values():
                    role=deepcopy(next(r for r in scenario_cfg['roles'] if r['category']=='towel'));role['max_instances']=3
                    scenario_cfg.update(roles=[role],eligible_categories=['towel'],required_categories=['towel'],allowed_support_tags=[supports[index]])
                for ordinal,level in enumerate(['low','medium','high'],start=1):
                    target=policy['levels'][level];target.update(count_ranges={s:[ordinal,ordinal] for s in policy['scenarios']},
                        eligible_categories=['towel'],allowed_pose_tags=['flat'],extra_required_categories=[],allowed_states={'towel':[state]},
                        required_state_counts={'s0_towel/'+state:ordinal},state_proportions={'towel':{state:1.}})
                validate_contract(policy,'Policy');inputs=Inputs(base.profile,base.catalog,policy,base.bindings,base.source_lock)
                plan=plan_requests(inputs,8100+len(records),scenario,'low');placed=place_requests(plan,room,inputs.catalog)
                write_json_new(run/'request.json',plan);write_json_new(run/'fixture_policy.json',policy)
                write_json_new(run/'profile.json',inputs.profile);write_json_new(run/'catalog.json',inputs.catalog);write_json_new(run/'source_lock.json',inputs.source_lock)
                write_json_new(run/'deployment.json',dict(bindings=inputs.bindings,rooms={room_id:'profile.json'},catalog='catalog.json',policy='fixture_policy.json',source_lock='source_lock.json',isaac_root='C:/isaac_sim'))
                attempt=run/'attempts/a000';attempt.mkdir(parents=True);write_json_new(attempt/'sampling.json',placed['sampling'])
                if placed['status']!='PASS':
                    write_json_new(attempt/'failure.json',placed['failure']);raise RuntimeError('S0_PLACEMENT_FAILED: '+name)
                scene=attempt/'scene.usda';write_scene(scene,inputs,placed);manifest=build_manifest(inputs,plan,placed,scene,name)
                static=validate_static(scene,manifest,room,inputs);integrity=validate_integrity(inputs,manifest);replay=replay_manifest(manifest,attempt/'replay',inputs,scene)
                validation=attempt/'validation';validation.mkdir()
                for kind,report in [('static',static),('integrity',integrity),('replay',replay)]:
                    write_json_new(validation/(kind+'.json'),report);manifest['evidence_refs'].append(dict(kind=kind,uri='validation/'+kind+'.json',sha256=sha256_file(validation/(kind+'.json')),
                        execution=report['execution'],outcome=report['outcome'],scope=report['scope'],target_state_digest=manifest['scene']['state_digest'],producer_identity=dict(code_hash=manifest['inputs']['code_hash'])))
                manifest['limits'].append('Dedicated S0 fixture; formal36 count/coverage acceptance not claimed.');seal_manifest(manifest,attempt/'manifest.json')
                record=dict(room=room_id,state=state,scenario=scenario,support=supports[index],manifest=str(attempt/'manifest.json'),outcome='PASS' if all(r['outcome']=='PASS' for r in [static,integrity,replay]) else 'FAIL')
                records.append(record);print(json.dumps(record),flush=True)
    write_json_new(out/'eight_case_results.json',dict(cases=records,scope='Static/Replay/Integrity only; Native Support and Visual pending'))
    raise SystemExit(0 if len(records)==8 and all(r['outcome']=='PASS' for r in records) else 5)
