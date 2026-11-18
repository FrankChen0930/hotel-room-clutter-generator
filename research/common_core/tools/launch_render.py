"""Launch one native renderer with an immutable dispatch claim and watchdog."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.contracts import load_json
from common_core.identity import sha256_file
from common_core.manifest import write_json_new
from common_core.paths import guard_new_output
from common_core.manifest import code_identity
from launch_native import working_set


if __name__=='__main__':
    parser=argparse.ArgumentParser();select=parser.add_mutually_exclusive_group(required=True);select.add_argument('--manifest',type=Path);select.add_argument('--batch',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cameras',type=Path);parser.add_argument('--timeout',type=int,default=300);args=parser.parse_args()
    def prepare(manifest,cameras):
        manifest=Path(manifest).resolve(strict=True);data=load_json(manifest)
        return dict(manifest=str(manifest),manifest_sha256=sha256_file(manifest),scene_sha256=data['scene']['sha256'],state_digest=data['scene']['state_digest'],cameras=cameras)
    if args.batch:
        batch=load_json(args.batch);request=dict(cases=[prepare(item['manifest'],item['cameras']) for item in batch['cases']])
    else:
        if not args.cameras:raise ValueError('CAMERAS_REQUIRED')
        request=prepare(args.manifest,load_json(args.cameras))
    if args.timeout<1:raise ValueError('WATCHDOG_TIMEOUT_INVALID')
    request.update(worker_sha256=sha256_file(CODE/'common_core/render.py'),producer_code_hash=code_identity())
    out=guard_new_output(args.output);out.mkdir(parents=True)
    write_json_new(out/'request.json',request);write_json_new(out/'dispatch_claim.json',dict(dispatched_utc=datetime.now(timezone.utc).isoformat(),timeout_s=args.timeout,automatic_redispatch=False))
    sdk=Path(sys.executable).resolve().parents[2];env={**os.environ,'PYTHONPATH':str(sdk/'site'),'ISAAC_PATH':str(sdk),'EXP_PATH':str(sdk/'apps'),'CARB_APP_PATH':str(sdk/'kit'),'PYTHONDONTWRITEBYTECODE':'1'}
    command=[sys.executable,'-B',str(CODE/'common_core/render.py'),'--request',str(out/'request.json')]
    start=time.monotonic();timed_out=False;peak=0;reason=None
    with (out/'process.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
        while process.poll() is None:
            rss=working_set(process)
            if rss is not None:peak=max(peak,rss)
            if time.monotonic()-start>args.timeout:timed_out=True;reason='WATCHDOG_TIMEOUT'
            elif rss is not None and rss>16*1024**3:reason='RSS_LIMIT'
            if reason:process.kill();break
            time.sleep(.2)
        exit_code=process.wait()
    result=dict(command=command,native_exit_code=exit_code,timed_out=timed_out,elapsed_s=time.monotonic()-start,
                peak_working_set_bytes=peak or None,termination_reason=reason,
                outcome='PASS' if exit_code==0 and ((out/'render.json').exists() or (out/'render_index.json').exists()) else 'INCOMPLETE',scope='native capture process only; visual review separate')
    write_json_new(out/'process.json',result);print(json.dumps(result));raise SystemExit(0 if result['outcome']=='PASS' else 6)
