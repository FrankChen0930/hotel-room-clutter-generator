"""Actual native fixture integration and simulated stale-evidence rejection gates."""
from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import patch
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.contracts import load_json
from common_core.identity import content_digest
from common_core.manifest import write_json_new
from common_core.room import load_inputs
from common_core.qualification import assess,verify

base=CODE.parent/'_common_core_runs/work_units/WU-16/a000'
directory=base/'native-current-runtime'
inputs=load_inputs(CODE.parent/'_common_core_runs/work_units/WU-15/a001/control/deployment.json','yazhi')
record=load_json(base/'qualified/qualification.json');verify(record,inputs)
original=load_json
mutations={
    'runtime':lambda c:c['runtime_fingerprint']['gpu']['devices'][0].update(driver_version='changed'),
    'physical_settings':lambda c:c['physics'].update(hz=60),
    'collider':lambda c:c['targets'][0].update(proxy_geometry_hash='changed'),
    'support_transform':lambda c:c['targets'][0]['support']['world_matrix'][3].__setitem__(0,9),
    'pose':lambda c:c['targets'][0]['initial_world_matrix'][3].__setitem__(0,9),
    'source':lambda c:c.update(source_closure_hash='changed'),
    'asset_state':lambda c:c.update(state_digest='changed'),
    'scene':lambda c:c.update(scene_sha256='changed'),
}
gates={}
for name,mutation in mutations.items():
    case=deepcopy(original(directory/'case.json'));mutation(case)
    claim=deepcopy(original(directory/'dispatch_claim.json'));claim['case_hash']=content_digest(case)
    def read(path):
        path=Path(path)
        if path==directory/'case.json':return case
        if path==directory/'dispatch_claim.json':return claim
        return original(path)
    with patch('common_core.qualification.load_json',side_effect=read):
        try:assess(directory,inputs)
        except ValueError as error:gates[name]=dict(outcome='PASS',rejection=str(error))
        else:raise AssertionError('STALE_ACCEPTED: '+name)
changed=deepcopy(record);changed['identity']['evidence']['process.log']='changed'
try:verify(changed,inputs)
except ValueError as error:gates['evidence']=dict(outcome='PASS',rejection=str(error))
else:raise AssertionError('CHANGED_EVIDENCE_ACCEPTED')
write_json_new(base/'unit-gates.json',dict(execution='EXECUTED',outcome='PASS',fresh_native_qualification=True,negative_gates=gates,
    scope='Exact engineering fixture only; release representative and visual acceptance remain later units'))
print(gates)
