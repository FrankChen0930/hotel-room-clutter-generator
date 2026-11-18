"""Relocated code, remounted protected inputs, new outputs and negative gates."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.identity import sha256_file
from common_core.manifest import write_json_new
from common_core.package import build_package

base=CODE.parent/'_common_core_runs/work_units/WU-18/a000';base.mkdir(parents=True,exist_ok=True)
delivery=build_package(base/'code delivery with spaces');relocated=delivery/'Common Core code'
config=json.loads((CODE/'config/deployment.local.json').read_text());lock=json.loads((CODE/'config/source_lock.json').read_text())
mounts={key:base/'remounted sources'/key for key in config['bindings']}
records=[*lock['helpers'],*lock['assets'],*[r for room in lock['rooms'].values() for r in room['closure']]]
for record in records:
    old=Path(config['bindings'][record['mount']])/record['path'];new=mounts[record['mount']]/record['path']
    if new.exists():continue
    new.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old,new)
    assert sha256_file(new)==record['sha256']
config['bindings']={key:str(path) for key,path in mounts.items()}
new_config=relocated/'config/researcher.local.json';write_json_new(new_config,config)
commands=[]
def run(name,entry,cfg,argv,expected):
    command=[sys.executable,'-B',str(entry),'--config'] if False else [sys.executable,'-B',str(entry),argv[0],'--config',str(cfg),*argv[1:]]
    process=subprocess.run(command,cwd=base,capture_output=True,text=True)
    log=base/(name+'.txt');log.write_text(process.stdout+process.stderr,encoding='utf-8')
    if process.returncode!=expected:raise AssertionError((name,process.returncode,process.stderr))
    commands.append(dict(name=name,command=command,exit_code=process.returncode,log=log.name,sha256=sha256_file(log)))
digests=[]
for room,scenario,level,seed in [('hotel705','STAYOVER','low',706),('yazhi','CHECKOUT','medium',707)]:
    values=[]
    for label,entry,cfg in [('original',CODE/'run_core.py',CODE/'config/deployment.local.json'),('relocated',relocated/'run_core.py',new_config)]:
        output=base/(room+' '+label)
        run(room+'-'+label,entry,cfg,['generate','--room',room,'--scenario',scenario,'--level',level,'--seed',str(seed),'--output',str(output)],0)
        manifest=output/'attempts/a000/manifest.json';values.append(json.loads(manifest.read_text())['scene']['state_digest'])
        if label=='relocated':
            run(room+'-replay',entry,cfg,['replay','--manifest',str(manifest),'--output',str(base/(room+' replay new path'))],0)
            run(room+'-validate',entry,cfg,['validate','--manifest',str(manifest),'--output',str(base/(room+' validation new path'))],0)
    assert values[0]==values[1];digests.append(dict(room=room,state_digest=values[0],same_after_code_and_source_remount=True))
asset=next(r for r in lock['assets'] if r['mount']=='room_yazhi');asset_path=mounts[asset['mount']]/asset['path'];hidden=asset_path.with_name(asset_path.name+'.missing')
assert asset_path.resolve().is_relative_to(base.resolve()) and not hidden.exists()
asset_path.rename(hidden)
try:run('missing-asset',relocated/'run_core.py',new_config,['preflight','--room','yazhi'],3)
finally:hidden.rename(asset_path)
bad_profile=json.loads((relocated/'config/rooms/yazhi.json').read_text());bad_profile['schema_version']='999.0'
write_json_new(relocated/'config/rooms/unsupported.json',bad_profile);bad_config=dict(config,rooms=dict(config['rooms'],yazhi='rooms/unsupported.json'))
write_json_new(relocated/'config/unsupported.local.json',bad_config)
run('unsupported-version',relocated/'run_core.py',relocated/'config/unsupported.local.json',['preflight','--room','yazhi'],2)
run('source-output',relocated/'run_core.py',new_config,['generate','--room','yazhi','--scenario','STAYOVER','--level','low','--seed','706','--output',str(mounts['room_yazhi']/'forbidden output')],7)
assert not (mounts['room_yazhi']/'forbidden output').exists()
inventory=json.loads((delivery/'inventory.json').read_text())
assert all(sha256_file(relocated/r['path'])==r['sha256'] for r in inventory['files'])
write_json_new(base/'unit-gates.json',dict(execution='EXECUTED',outcome='PASS',commands=commands,reproduction=digests,
    delivery=str(delivery),external_assets_not_packaged=True,source_copies_scope='Internal verification evidence only, separate from code-only delivery',
    negatives=['missing asset exit3','unsupported version exit2','source output rejected exit7']))
print('RELOCATED_REPRO_PASS')
