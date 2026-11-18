"""Exercise all public commands using new evidence and fixed seeds."""
import json
from pathlib import Path
import subprocess
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.manifest import write_json_new
from common_core.identity import sha256_file
base=CODE.parent/'_common_core_runs/work_units/WU-17/a000';base.mkdir(parents=True,exist_ok=True)
config=CODE/'config/deployment.local.json';records=[]
def run(name,argv,expected):
    command=[sys.executable,'-B',str(CODE/'run_core.py'),*argv]
    result=subprocess.run(command,cwd=base,capture_output=True,text=True)
    log=base/(name+'.txt');log.write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode!=expected:raise AssertionError((name,result.returncode,result.stderr))
    records.append(dict(name=name,command=command,exit_code=result.returncode,log=log.name,sha256=sha256_file(log)))
run('preflight',['preflight','--config',str(config),'--room','yazhi'],0)
assert set(p.name for p in base.iterdir())=={'preflight.txt'}
spec=dict(schema='Batch/1',cases=[dict(case_key='expected_failure',room='missing',scenario='STAYOVER',level='low',seed=706),
    dict(case_key='continued',room='yazhi',scenario='STAYOVER',level='low',seed=707)])
write_json_new(base/'isolation-spec.json',spec)
run('batch',['batch','--config',str(config),'--spec',str(base/'isolation-spec.json'),'--output',str(base/'batch')],5)
index=json.loads((base/'batch/batch_index.json').read_text());assert [r['exit_code'] for r in index['cases']]==[2,0]
manifest=base/'batch/continued/attempts/a000/manifest.json'
before=sha256_file(manifest)
run('validate',['validate','--config',str(config),'--manifest',str(manifest),'--tiers','integrity,static,replay','--output',str(base/'assessment')],0)
run('replay',['replay','--config',str(config),'--manifest',str(manifest),'--output',str(base/'replay with spaces')],0)
run('existing-output',['generate','--config',str(config),'--room','yazhi','--scenario','STAYOVER','--level','low','--seed','707','--output',str(base/'batch/continued')],7)
run('unknown-tier',['validate','--config',str(config),'--manifest',str(manifest),'--tiers','unknown','--output',str(base/'never-created')],2)
assert not (base/'never-created').exists() and sha256_file(manifest)==before
write_json_new(base/'unit-gates.json',dict(execution='EXECUTED',outcome='PASS',commands=records,
    gates=['five commands exercised (generate via batch)','preflight no scene or run','failed case retained and next case executed','fixed seeds','new output guard','sealed manifest unchanged']))
print('PUBLIC_CLI_GATES_PASS')
