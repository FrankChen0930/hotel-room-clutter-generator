"""Launch one native preview session for multiple newly converted models."""
import argparse
import os
from pathlib import Path
import subprocess
import time
from library import ROOT,write,sha

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--jobs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=int,default=1200);a=p.parse_args()
    out=a.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('NEW_WORKLINE_OUTPUT_REQUIRED')
    sdk=Path('C:/isaac_sim');env={**os.environ,'PYTHONPATH':str(sdk/'site'),'ISAAC_PATH':str(sdk),'EXP_PATH':str(sdk/'apps'),
        'CARB_APP_PATH':str(sdk/'kit'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
    command=[str(sdk/'kit/python/python.exe'),'-B',str(ROOT/'scripts/render_asset_batch.py'),'--jobs',str(a.jobs.resolve()),'--output',str(out)]
    started=time.monotonic();timed_out=False
    with out.with_suffix('.process.log').open('x',encoding='utf-8') as stream:
        proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        try:code=proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:proc.kill();code=proc.wait();timed_out=True
    report=dict(outcome='PASS' if code==0 and (out/'batch_result.json').is_file() else 'FAIL',native_exit_code=code,timed_out=timed_out,
        elapsed_s=round(time.monotonic()-started,2),worker_sha256=sha(ROOT/'scripts/render_asset_batch.py'),jobs_sha256=sha(a.jobs))
    write(out.with_suffix('.process.json'),report);print(report);raise SystemExit(report['outcome']!='PASS')
