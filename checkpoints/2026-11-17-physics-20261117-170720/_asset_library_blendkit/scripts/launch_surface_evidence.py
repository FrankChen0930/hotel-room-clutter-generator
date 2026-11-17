"""Bounded native support or fixed-camera rendering for the measured-surface candidate."""
import argparse,os,runpy,subprocess,sys,time
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--kind',choices=['support','render'],required=True)
    p.add_argument('--render-batch',type=Path);p.add_argument('--render-output',type=Path);a=p.parse_args()
    run=a.run.resolve();assert run.is_relative_to(ROOT/'runs')
    if a.kind=='render':
        import usd_sdk
        usd_sdk.load();core=ROOT.parent/'common_core';sys.path.insert(0,str(core));sys.path.insert(0,str(core/'tools'))
        import common_core.paths
        common_core.paths.RUN_ROOT=ROOT/'runs'
        worker=core/'tools/launch_render.py';sys.argv=[str(worker),'--batch',str((a.render_batch or run/'render_batch.json').resolve()),'--output',str((a.render_output or run/'native_render').resolve()),'--timeout','1200']
        runpy.run_path(str(worker),run_name='__main__');return
    out=run/'native_support';out.mkdir(exist_ok=False);cases=[]
    for case in read(run/'cases.json')['cases']:
        source=read(Path(case['manifest']).parent/'contact_samples.json');queries=[]
        specs={s['support_id']:s for s in read(Path(case['config']).parent/'surfaces.json')['surfaces']}
        for c in source['contacts']:
            queries.append(dict(instance_id=c['instance_id'],support_id=c['support_id'],expected=specs[c['support_id']]['collider'],points=c['fit']['points'],heights=c['fit']['heights']))
        cases.append(dict(scene=case['scene'],scene_sha256=sha(case['scene']),manifest=case['manifest'],manifest_sha256=sha(case['manifest']),queries=queries))
    write(out/'request.json',dict(cases=cases));sdk=Path('C:/isaac_sim')
    env={**os.environ,'PYTHONPATH':str(sdk/'site'),'ISAAC_PATH':str(sdk),'EXP_PATH':str(sdk/'apps'),'CARB_APP_PATH':str(sdk/'kit'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
    started=time.monotonic();command=[sys.executable,'-B',str(ROOT/'scripts/native_surface_queries.py'),'--request',str(out/'request.json')]
    with (out/'process.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:code=process.wait(timeout=900)
        except subprocess.TimeoutExpired:process.kill();code=process.wait()
    outcome='PASS' if code==0 and (out/'result.json').exists() and read(out/'result.json')['outcome']=='PASS' else 'FAIL'
    write(out/'process.json',dict(outcome=outcome,exit_code=code,elapsed_s=time.monotonic()-started,worker_sha256=sha(ROOT/'scripts/native_surface_queries.py')))
    print('SURFACE_SUPPORT_PROCESS',outcome,flush=True);raise SystemExit(outcome!='PASS')

if __name__=='__main__':main()
