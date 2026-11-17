"""Real controlled invalid-pose -> bounded resample -> one native retry fixture."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.contracts import load_json
from common_core.identity import sha256_file,state_digest
from common_core.manifest import build_manifest,seal_manifest,write_json_new
from common_core.paths import guard_new_output
from common_core.room import Inputs,RoomCache,load_inputs,prepare_room
from common_core.planner import plan_requests
from common_core.placer import place_requests
from common_core.repair import classify_native,repair
from common_core.writer import write_scene
from common_core.validation import validate_static,validate_integrity
from common_core.replay import replay_manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=guard_new_output(args.output);out.mkdir(parents=True);base=load_inputs(CODE/'config/deployment.local.json','yazhi');room=prepare_room(base.profile,base.bindings)
    policy=deepcopy(base.policy);policy.update(policy_id='BOUNDED_REPAIR_CONTROL_FIXTURE',release_frozen=False)
    for scenario in policy['scenarios'].values():
        scenario.update(eligible_categories=['book'],required_categories=['book'],allowed_support_tags=['cabinet'],roles=[next(r for r in scenario['roles'] if r['category']=='book')])
    for ordinal,level in enumerate(['low','medium','high'],1):
        policy['levels'][level].update(count_ranges={s:[ordinal,ordinal] for s in policy['scenarios']},eligible_categories=['book'],extra_required_categories=[],allowed_states={},required_state_counts={},state_proportions={},spread=dict(hard=False,target=None))
    inputs=Inputs(base.profile,base.catalog,policy,base.bindings,base.source_lock);plan=plan_requests(inputs,9101,'STAYOVER','low');placed=place_requests(plan,room,inputs.catalog)
    write_json_new(out/'request.json',dict(plan=plan,fixture='deliberate25mm initial penetration, not a release scene'))
    for name,data in [('profile.json',inputs.profile),('catalog.json',inputs.catalog),('policy.json',policy),('source_lock.json',inputs.source_lock)]:write_json_new(out/name,data)
    write_json_new(out/'deployment.json',dict(bindings=inputs.bindings,rooms=dict(yazhi='profile.json'),catalog='catalog.json',policy='policy.json',source_lock='source_lock.json',isaac_root='C:/isaac_sim'))
    broken=deepcopy(placed)
    for key in ['after','effective']:
        broken['objects'][0][key]=deepcopy(broken['objects'][0][key]);broken['objects'][0][key]['world_matrix'][3][2]-=.025
    def candidate(ordinal,placements,parent=None):
        attempt=out/'attempts'/f'a{ordinal:03d}';attempt.mkdir(parents=True);scene=attempt/'scene.usda';write_scene(scene,inputs,placements)
        write_json_new(attempt/'sampling.json',placements['sampling'])
        manifest=build_manifest(inputs,plan,placements,scene,out.name,f'a{ordinal:03d}');manifest['parent_attempt_id']=parent
        if parent:manifest['attempt_lineage']=[dict(attempt_id=parent,manifest_sha256=sha256_file(out/'attempts'/parent/'manifest.json'),outcome='FAIL')]
        reports=dict(static=validate_static(scene,manifest,room,inputs),integrity=validate_integrity(inputs,manifest),replay=replay_manifest(manifest,attempt/'replay',inputs,scene))
        validation=attempt/'validation';validation.mkdir()
        for kind,report in reports.items():
            write_json_new(validation/(kind+'.json'),report);manifest['evidence_refs'].append(dict(kind=kind,uri='validation/'+kind+'.json',sha256=sha256_file(validation/(kind+'.json')),
                execution=report['execution'],outcome=report['outcome'],scope=report['scope'],target_state_digest=manifest['scene']['state_digest'],producer_identity=dict(code_hash=manifest['inputs']['code_hash'])))
        seal_manifest(manifest,attempt/'manifest.json');return attempt,reports
    def native(attempt):
        output=attempt/'native';command=[sys.executable,'-B',str(CODE/'tools/launch_native.py'),'--manifest',str(attempt/'manifest.json'),'--room','yazhi','--asset','book','--output',str(output)]
        process=subprocess.run(command,cwd=CODE,capture_output=True,text=True);(attempt/'native-dispatch.log').write_text(process.stdout+process.stderr,encoding='utf-8')
        return load_json(output/'result.json') if (output/'result.json').exists() else None,load_json(output/'process.json')
    first,reports=candidate(0,broken);original_sha=sha256_file(first/'manifest.json')
    if reports['static']['outcome']!='FAIL':raise RuntimeError('CONTROLLED_STATIC_FAILURE_NOT_OBSERVED')
    failed,process=native(first);kind=classify_native(failed,process,reports['static']);decision=repair(plan,broken,dict(failure_kind=kind,attempt_id='a000'),dict(native_retries_used=0))
    write_json_new(out/'repair_decision.json',decision)
    if failed is None or failed['outcome']!='FAIL' or decision['action']!='NEW_ATTEMPT':raise RuntimeError('CONTROLLED_NATIVE_FAILURE_NOT_REPAIRABLE: '+kind)
    corrected=place_requests(plan,room,inputs.catalog,stream='repair',attempt_ordinal=1,preferred_supports=decision['preferred_supports'],sample_limits=decision['remaining_samples'])
    if corrected['status']!='PASS':raise RuntimeError('REPAIR_GEOMETRY_EXHAUSTED')
    second,second_reports=candidate(1,corrected,'a000');passed,second_process=native(second)
    if passed is None or passed['outcome']!='PASS' or second_process['native_exit_code']!=0 or second_reports['static']['outcome']!='PASS':raise RuntimeError('REPAIR_NATIVE_RETRY_FAILED')
    if sha256_file(first/'manifest.json')!=original_sha:raise RuntimeError('FAILED_ATTEMPT_MUTATED')
    impossible=RoomCache(room.cache_key,room.source_path,room.source_identity,room.supports,room.obstacles,room.native_initial,({'bounds':[[-100,-100,-100],[100,100,100]]},))
    no_solution=place_requests(plan,impossible,inputs.catalog,stream='repair',attempt_ordinal=1)
    if no_solution['status']!='FAIL':raise RuntimeError('IMPOSSIBLE_FIXTURE_NOT_REJECTED')
    write_json_new(out/'terminal_no_solution.json',dict(status='FAIL',reason='GEOMETRY_BUDGET_EXHAUSTED',result=no_solution,plan=plan,forbidden_regions=list(impossible.forbidden_regions),native_dispatches=0,required_requests_dropped=False))
    exhausted=repair(plan,corrected,dict(failure_kind='UNSTABLE',attempt_id='a001'),dict(native_retries_used=1));write_json_new(out/'exhausted_budget.json',exhausted)
    write_json_new(out/'result.json',dict(execution='EXECUTED',outcome='PASS',native_dispatches=2,native_retries=1,failed_attempt_retained=True,
        failure_kind=kind,parent_attempt='a000',selected_attempt='a001',impossible_fixture='terminal_no_solution.json',exhausted_budget=exhausted,
        scope='controlled repair/terminal controller fixtures; no release scene or asset-global qualification'))
    print('NATIVE_REPAIR_AND_TERMINAL_FIXTURES_PASS',flush=True)
