"""Bounded real full-room simulation, retaining failures as diagnostic evidence."""
import argparse,os,sys,subprocess,time,shutil
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode',choices=['authored','props_dynamic','source_fixed_props_dynamic'],default='authored');p.add_argument('--seconds',type=float,default=10);p.add_argument('--perturb-seed',type=int);a=p.parse_args()
    out=a.output.resolve();assert out.is_relative_to(ROOT/'runs');out.mkdir(parents=True,exist_ok=False)
    assert 0<a.seconds<=30
    cfg=dict(scene=str(a.scene.resolve()),scene_sha256=sha(a.scene),seconds=a.seconds,mode=a.mode,generated_bodies={},perturb_seed=a.perturb_seed)
    if a.manifest:
        import usd_sdk
        usd_sdk.load();sys.path.insert(0,str(ROOT.parent/'common_core'))
        from common_core.writer import object_prim
        records={r['asset_id']:r for r in read(ROOT/'registry/assets.json')['assets']}
        for obj in read(a.manifest)['objects']:
            record=records.get(obj['asset_id'],{})
            request=next((r for r in read(a.manifest).get('requests',[]) if r['request_id']==obj['request_id']),{})
            cfg['generated_bodies'][object_prim(obj)]=dict(asset_id=obj['asset_id'],category=record.get('category',request.get('category')),name=record.get('name',''),support_id=obj['effective']['support_id'])
        cfg['manifest_sha256']=sha(a.manifest)
        from expanded_surfaces import CURVED
        cfg['support_colliders']={key:value[0] for key,value in CURVED.items()}
    for name in ['room_dynamic_worker.py','dynamic_preflight.py']:shutil.copy2(ROOT/'scripts'/name,out/name)
    cfg['producer_snapshot']={name:sha(out/name) for name in ['room_dynamic_worker.py','dynamic_preflight.py']}
    write(out/'request.json',cfg);sdk=Path('C:/isaac_sim')
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(sdk/'site'),str(ROOT.parent/'common_core'),str(ROOT/'scripts')]),'ISAAC_PATH':str(sdk),'EXP_PATH':str(sdk/'apps'),'CARB_APP_PATH':str(sdk/'kit'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
    started=time.monotonic()
    with (out/'process.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen([sys.executable,'-B',str(out/'room_dynamic_worker.py'),'--request',str(out/'request.json')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:code=process.wait(timeout=600)
        except subprocess.TimeoutExpired:process.kill();code=process.wait()
    report=dict(process_exit_code=code,elapsed_s=time.monotonic()-started,result=read(out/'result.json')['outcome'] if (out/'result.json').exists() else 'NO_RESULT')
    write(out/'process.json',report);print('FULL_ROOM_DYNAMIC_PROCESS',report);raise SystemExit(code!=0)

if __name__=='__main__':main()
