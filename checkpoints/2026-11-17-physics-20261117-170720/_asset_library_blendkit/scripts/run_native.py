"""Launch native capture with bounded runtime and an isolated local cache."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from library import ROOT, write, sha

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--usd',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=240); p.add_argument('--scope',default='ASSET_CAPTURE_PENDING_VISUAL_REVIEW'); a=p.parse_args()
    if a.timeout<1: raise ValueError('INVALID_TIMEOUT')
    out=a.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT): raise ValueError('NEW_LIBRARY_OUTPUT_REQUIRED')
    out.parent.mkdir(parents=True,exist_ok=True)
    log=out.with_suffix('.process.log')
    sdk=Path('C:/isaac_sim'); env={**os.environ,'PYTHONPATH':str(sdk/'site'),'ISAAC_PATH':str(sdk),
        'EXP_PATH':str(sdk/'apps'),'CARB_APP_PATH':str(sdk/'kit'),'PYTHONDONTWRITEBYTECODE':'1'}
    command=[str(sdk/'kit/python/python.exe'),'-B',str(ROOT/'scripts/render_isaac.py'),
             '--usd',str(a.usd.resolve(strict=True)),'--output',str(out),'--scope',a.scope]
    start=time.monotonic(); timed_out=False
    with log.open('x',encoding='utf-8') as f:
        proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        try: code=proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            proc.kill(); code=proc.wait(); timed_out=True
    report=dict(outcome='PASS' if code==0 and (out/'render.json').is_file() else 'FAIL',
        native_exit_code=code,timed_out=timed_out,elapsed_s=round(time.monotonic()-start,2),
        usd_sha256=sha(a.usd),worker_sha256=sha(ROOT/'scripts/render_isaac.py'),scope=a.scope)
    write(out.with_suffix('.process.json'),report); print(report); raise SystemExit(report['outcome']!='PASS')
