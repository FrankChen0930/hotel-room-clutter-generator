"""Dispatch a bounded batch of native support queries into a new assessment."""
import argparse
import copy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from launch_native import working_set
from common_core.contracts import load_json,validate_contract
from common_core.identity import content_digest,sha256_file,state_digest
from common_core.manifest import write_json_new
from common_core.paths import guard_new_output
from common_core.room import load_inputs,prepare_room
from common_core.validation import composed_footprint
from common_core.writer import object_prim
from pxr import Usd


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--batch',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=CODE/'config/deployment.local.json')
    parser.add_argument('--negative-fixtures',action='store_true');parser.add_argument('--timeout',type=int,default=300);args=parser.parse_args()
    batch=load_json(args.batch);out=guard_new_output(args.output);cases=[];cache={}
    for item in batch['cases']:
        room_id=item['room']
        if room_id not in cache:
            inputs=load_inputs(args.config,room_id);cache[room_id]=(inputs,prepare_room(inputs.profile,inputs.bindings))
        inputs,room=cache[room_id];path=Path(item['manifest']).resolve(strict=True);manifest=validate_contract(load_json(path),'Manifest');scene=path.parent/'scene.usda'
        if state_digest(manifest)!=manifest['scene']['state_digest'] or sha256_file(scene)!=manifest['scene']['sha256']:raise ValueError('SUPPORT_SCENE_STATE_IDENTITY')
        stage=Usd.Stage.Open(str(scene));queries=[];ignored=[]
        for obj in manifest['objects']:
            prim_path=object_prim(obj);ignored.append(prim_path);footprint=composed_footprint(stage,stage.GetPrimAtPath(prim_path));count=len(footprint)
            center=[sum(p[j] for p in footprint)/count for j in range(2)]
            points=[center,*footprint,*[[(footprint[i][j]+footprint[(i+1)%count][j])/2 for j in range(2)] for i in range(count)]]
            support_id=obj['effective']['support_id'];spec=next(s for s in inputs.profile['supports'] if s['support_id']==support_id)
            queries.append(dict(instance_id=obj['instance_id'],points=points,support_z=room.supports[support_id]['z'],expected_collider=spec['collider']))
        cases.append(dict(scene=str(scene),scene_sha256=sha256_file(scene),manifest=str(path),manifest_sha256=sha256_file(path),state_digest=state_digest(manifest),queries=queries,ignored=ignored))
    if args.negative_fixtures:
        wrong=copy.deepcopy(cases[0]);wrong['queries']=wrong['queries'][:1];wrong['queries'][0]['expected_collider']='/Incorrect/Source';wrong['expect_outcome']='FAIL';cases.append(wrong)
        missing=copy.deepcopy(cases[0]);missing['queries']=missing['queries'][:1];missing['queries'][0]['points']=[[10000.,10000.]];missing['expect_outcome']='FAIL';cases.append(missing)
    out.mkdir(parents=True);request=dict(cases=cases);write_json_new(out/'request.json',request)
    write_json_new(out/'dispatch_claim.json',dict(dispatched_utc=datetime.now(timezone.utc).isoformat(),request_hash=content_digest(request),timeout_s=args.timeout,rss_limit_gib=16,automatic_redispatch=False))
    sdk=Path(sys.executable).resolve().parents[2];env={**os.environ,'PYTHONPATH':str(sdk/'site'),'ISAAC_PATH':str(sdk),'EXP_PATH':str(sdk/'apps'),'CARB_APP_PATH':str(sdk/'kit'),'PYTHONDONTWRITEBYTECODE':'1'}
    command=[sys.executable,'-B',str(CODE/'common_core/support_validation.py'),'--request',str(out/'request.json')];start=time.monotonic();peak=0;reason=None
    with (out/'process.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
        while process.poll() is None:
            rss=working_set(process)
            if rss is not None:peak=max(peak,rss)
            if time.monotonic()-start>args.timeout:reason='WATCHDOG_TIMEOUT'
            elif rss is not None and rss>16*1024**3:reason='RSS_LIMIT'
            if reason:process.kill();break
            time.sleep(.2)
        exit_code=process.wait()
    report=dict(command=command,native_exit_code=exit_code,elapsed_s=time.monotonic()-start,peak_working_set_bytes=peak or None,termination_reason=reason,
                outcome='PASS' if exit_code==0 and (out/'result.json').exists() else 'INCOMPLETE',scope='process plus fixture expectations; per-scene ray outcomes separate')
    write_json_new(out/'process.json',report);print(json.dumps(report));raise SystemExit(0 if report['outcome']=='PASS' else 6)
