"""Generate exactly the frozen release keys and native batch input lists."""
from pathlib import Path
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.cli import main
from common_core.contracts import load_json
from common_core.manifest import write_json_new
base=CODE.parent/'_common_core_runs/work_units/WU-20/a000';base.mkdir(parents=True,exist_ok=True)
config=CODE/'config/deployment.local.json';spec=CODE/'config/batch_v1.json'
exit_code=main(['batch','--config',str(config),'--spec',str(spec),'--output',str(base/'formal36')])
if exit_code:raise SystemExit(exit_code)
cases=[]
for case in load_json(spec)['cases']:
    profile=load_json(CODE/'config/rooms'/(case['room']+'.json'))
    cameras={c['camera_id']:dict(eye=c['eye'],target=c['target'],focal=c['focal']) for c in profile['cameras']}
    cases.append(dict(room=case['room'],case_key=case['case_key'],manifest=str(base/'formal36'/case['case_key']/'attempts/a000/manifest.json'),cameras=cameras))
write_json_new(base/'native-batch.json',dict(cases=cases))
print('FORMAL36_GENERATION_PASS')
