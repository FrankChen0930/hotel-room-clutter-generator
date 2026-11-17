"""Final executed scopes, stale-scope guards and actual changed-image negative."""
from copy import deepcopy
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path(sys.executable).resolve().parents[2])
from common_core.contracts import load_json
from common_core.identity import content_digest,sha256_file
from common_core.manifest import write_json_new
from common_core.room import load_inputs,Inputs
from common_core.qualification import qualify,verify
from common_core.visual import verify_review

base=CODE.parent/'_common_core_runs/work_units/WU-21/a000';scopes=[]
for room,label in [('hotel705','hotel'),('yazhi','yazhi')]:
    inputs=load_inputs(CODE/'config/deployment.local.json',room);record=load_json(base/(label+'-qualified/qualification.json'));verify(record,inputs)
    identities=record['identity']['targets'];assert len(identities)==2
    assert {t['support']['proxy_kind'] for t in identities}=={'box','cylinder'}
    scopes.append(dict(room=room,qualification=str(base/(label+'-qualified/qualification.json')),fingerprint=record['fingerprint'],
        support_geometry_types=sorted({t['support']['support_geometry_type'] for t in identities}),named_targets=[t['object']['instance_id'] for t in identities]))
inputs=load_inputs(CODE/'config/deployment.local.json','hotel705');directory=base/'hotel-final-two-body';record=load_json(base/'hotel-qualified/qualification.json')
review_path=Path(record['identity']['visual_review']['path']);original=load_json;gates={}
def rejects(name,operation,reason):
    try:operation()
    except ValueError as error:
        if reason not in str(error):raise
        gates[name]=dict(outcome='PASS',expected_rejection=reason,actual=str(error))
    else:raise AssertionError('STALE_SCOPE_ACCEPTED: '+name)
mutations={
    'source':(lambda c:c.update(source_closure_hash='changed'),'QUALIFICATION_SOURCE'),
    'state':(lambda c:c.update(state_digest='changed'),'QUALIFICATION_STATE'),
    'collider':(lambda c:c['targets'][0].update(proxy_geometry_hash='changed'),'QUALIFICATION_COLLIDER'),
    'support_transform':(lambda c:c['targets'][0]['support']['world_matrix'][3].__setitem__(0,9),'QUALIFICATION_SUPPORT'),
    'pose':(lambda c:c['targets'][0]['initial_world_matrix'][3].__setitem__(0,9),'QUALIFICATION_POSE'),
    'runtime':(lambda c:c['runtime_fingerprint']['gpu']['devices'][0].update(driver_version='changed'),'QUALIFICATION_RUNTIME'),
    'physical_settings':(lambda c:c['physics'].update(hz=60),'QUALIFICATION_PHYSICS')}
for name,(mutation,reason) in mutations.items():
    case=deepcopy(original(directory/'case.json'));mutation(case);claim=deepcopy(original(directory/'dispatch_claim.json'));claim['case_hash']=content_digest(case)
    def read(path):
        path=Path(path)
        return case if path==directory/'case.json' else claim if path==directory/'dispatch_claim.json' else original(path)
    with patch('common_core.qualification.load_json',side_effect=read):rejects(name,lambda:qualify(directory,inputs,review_path),reason)
catalog=deepcopy(inputs.catalog);catalog['entries'][0]['states'][0]['sha256']='0'*64
changed_inputs=Inputs(inputs.profile,catalog,inputs.policy,inputs.bindings,inputs.source_lock)
rejects('asset_state',lambda:qualify(directory,changed_inputs,review_path),'INPUT_IDENTITY_MISMATCH: catalog_hash')
def incomplete(path):
    value=original(path)
    if Path(path)==directory/'process.json':value=dict(value,native_exit_code=None,outcome='INCOMPLETE')
    return value
with patch('common_core.qualification.load_json',side_effect=incomplete):rejects('native_incomplete',lambda:qualify(directory,inputs,review_path),'QUALIFICATION_PROCESS')
def recorded(path):
    value=original(path)
    if Path(path)==directory/'result.json':value=dict(value,execution='RECORDED')
    return value
with patch('common_core.qualification.load_json',side_effect=recorded):rejects('recorded_pass',lambda:qualify(directory,inputs,review_path),'QUALIFICATION_RESULT')
def changed_hash(path):return '0'*64 if Path(path)==directory/'process.log' else sha256_file(path)
with patch('common_core.qualification.sha256_file',side_effect=changed_hash):rejects('evidence_log',lambda:verify(record,inputs),'QUALIFICATION_STALE')
tamper=base/'image-tamper';tamper.mkdir();review=deepcopy(original(review_path));item=review['images'][0];capture=Path(item['capture'])
shutil.copyfile(capture,tamper/'render.json');shutil.copyfile(capture.parent/item['path'],tamper/item['path'])
with (tamper/item['path']).open('ab') as stream:stream.write(b'ACTUAL_NEGATIVE_TEST_CHANGED_IMAGE_BYTES')
item.update(capture=str(tamper/'render.json'),capture_sha256=sha256_file(tamper/'render.json'))
write_json_new(tamper/'review.json',review)
manifest=Path(original(directory/'case.json')['manifest'])
rejects('changed_image_bytes',lambda:verify_review(tamper/'review.json',manifest),'VISUAL_IMAGE_HASH')
review['target_state_digest']='changed';write_json_new(tamper/'wrong-state-review.json',review)
rejects('image_state',lambda:verify_review(tamper/'wrong-state-review.json',manifest),'VISUAL_STATE_IDENTITY')
legacy=[original(base/'legacy-six'/str(i)/'legacy_replay.json') for i in range(6)]
assert all(r['outcome']=='PASS' for r in legacy)
assert {'Mesh','Cube'}<=set().union(*(set(s['support_geometry_types']) for s in scopes))
assert len(list(base.glob('*-final-two-body/dispatch_claim.json')))==2
write_json_new(base/'unit-gates.json',dict(execution='EXECUTED',outcome='PASS',exact_final_scopes=scopes,negative_gates=gates,
    fresh_legacy_six='PASS',repair_evidence='WU-15/a001 real native failure plus one bounded retry; no controller/worker physics change since acceptance',
    native_dispatches=2,whole_scene_dynamic_qualification=False,scope='Only two actual final native dispatches count as executed dynamics; guard substitutions are negative integration tests'))
print('FINAL_DYNAMICS_REGRESSION_GATES_PASS',len(gates))
