"""Prepare and dispatch one exact-pose feasibility case with bounded resources."""
import argparse
import ctypes
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path(sys.executable).resolve().parents[2])
from pxr import Usd,UsdPhysics
from common_core.contracts import load_json,validate_contract
from common_core.identity import content_digest,sha256_file,state_digest
from common_core.manifest import write_json_new
from common_core.native_validation import proxy_supported
from common_core.paths import guard_new_output
from common_core.room import load_inputs,prepare_room,geometry_signature
from common_core.writer import object_prim
from common_core.runtime import runtime_environment


def working_set(process):
    if os.name!='nt':return None
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in
            ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    ok=ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(process._handle)),ctypes.byref(counters),counters.cb)
    return counters.WorkingSetSize if ok else None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--room',required=True)
    parser.add_argument('--asset',required=True);parser.add_argument('--count',type=int,default=1);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=CODE/'config/deployment.local.json')
    parser.add_argument('--purpose',choices=['FEASIBILITY_ONLY','EXACT_FIXTURE','RELEASE_REPRESENTATIVE'],default='EXACT_FIXTURE')
    parser.add_argument('--timeout',type=int,default=240);parser.add_argument('--rss-gib',type=float,default=16);args=parser.parse_args()
    if args.count<1 or args.timeout<1 or args.rss_gib<=0:raise ValueError('NATIVE_BUDGET_OR_TARGET_COUNT')
    out=guard_new_output(args.output)
    for parent in out.parents:
        if parent.name=='WU-13' and len(list(parent.rglob('dispatch_claim.json')))>=4:raise ValueError('WU13_NATIVE_BUDGET_EXHAUSTED')
    manifest_path=args.manifest.resolve(strict=True);manifest=validate_contract(load_json(manifest_path),'Manifest');scene=manifest_path.parent/'scene.usda'
    if sha256_file(scene)!=manifest['scene']['sha256'] or state_digest(manifest)!=manifest['scene']['state_digest']:raise ValueError('NATIVE_SCENE_STATE_IDENTITY')
    inputs=load_inputs(args.config,args.room);room=prepare_room(inputs.profile,inputs.bindings)
    if manifest['inputs']['source_closure_hash']!=inputs.profile['source']['closure_sha256']:raise ValueError('NATIVE_SOURCE_CLOSURE_IDENTITY')
    stage=Usd.Stage.Open(str(scene));targets=[]
    asset_ids=args.asset.split(',');eligible=[o for o in manifest['objects'] if o['asset_id'] in asset_ids]
    objects=[]
    for asset_id in asset_ids:
        first=next((o for o in eligible if o['asset_id']==asset_id),None)
        if first is not None and len(objects)<args.count:objects.append(first)
    objects.extend(o for o in eligible if o not in objects and len(objects)<args.count)
    if len(objects)!=args.count:raise ValueError('NATIVE_TARGET_COUNT_UNAVAILABLE')
    for obj in objects:
        path=object_prim(obj);root=stage.GetPrimAtPath(path)
        shapes=[p for p in Usd.PrimRange(root,Usd.TraverseInstanceProxies()) if p.HasAPI(UsdPhysics.CollisionAPI)]
        if len(shapes)!=1:raise ValueError('NATIVE_PROXY_SHAPE_COUNT')
        shape=shapes[0];kind={'Cube':'box','Cylinder':'cylinder'}.get(shape.GetTypeName(),'none')
        if not proxy_supported(kind):raise ValueError('NATIVE_PROXY_UNSUPPORTED')
        support_id=obj['effective']['support_id'];support=room.supports[support_id];spec=next(s for s in inputs.profile['supports'] if s['support_id']==support_id)
        targets.append(dict(instance_id=obj['instance_id'],prim=path,shape=str(shape.GetPath()),proxy_kind=kind,
            proxy_geometry_hash=geometry_signature(shape),support=support,support_kind=spec['kind'],
            support_geometry_type=stage.GetPrimAtPath(spec['collider']).GetTypeName(),support_collider=spec['collider'],initial_world_matrix=obj['effective']['world_matrix']))
    case=dict(scene=str(scene),scene_sha256=sha256_file(scene),manifest=str(manifest_path),manifest_sha256=sha256_file(manifest_path),state_digest=state_digest(manifest),
        purpose=args.purpose,scope='Exact named targets only; remaining bodies frozen and joints disabled in unsaved session; qualification is a separate identity-bound record',
        targets=targets,source_closure_hash=inputs.profile['source']['closure_sha256'],runtime=inputs.source_lock['environment'],runtime_fingerprint=runtime_environment(),physics=dict(steps=240,hz=120,device='cpu',fabric=False))
    out.mkdir(parents=True);write_json_new(out/'case.json',case)
    write_json_new(out/'dispatch_claim.json',dict(dispatched_utc=datetime.now(timezone.utc).isoformat(),case_hash=content_digest(case),timeout_s=args.timeout,rss_limit_gib=args.rss_gib,automatic_redispatch=False))
    sdk=Path(sys.executable).resolve().parents[2];env={**os.environ,'PYTHONPATH':str(sdk/'site'),'ISAAC_PATH':str(sdk),'EXP_PATH':str(sdk/'apps'),'CARB_APP_PATH':str(sdk/'kit'),'PYTHONDONTWRITEBYTECODE':'1'}
    command=[sys.executable,'-B',str(CODE/'common_core/native_validation.py'),'--case',str(out/'case.json')]
    start=time.monotonic();peak=0;reason=None
    with (out/'process.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
        while process.poll() is None:
            rss=working_set(process)
            if rss is not None:peak=max(peak,rss)
            if time.monotonic()-start>args.timeout:reason='WATCHDOG_TIMEOUT'
            elif rss is not None and rss>args.rss_gib*1024**3:reason='RSS_LIMIT'
            if reason:process.kill();break
            time.sleep(.2)
        exit_code=process.wait()
    report=dict(command=command,native_exit_code=exit_code,elapsed_s=time.monotonic()-start,peak_working_set_bytes=peak or None,
                termination_reason=reason,outcome='PASS' if exit_code==0 and (out/'result.json').exists() else 'INCOMPLETE',scope='process completion only; result checks determine feasibility')
    write_json_new(out/'process.json',report);print(json.dumps(report));raise SystemExit(0 if report['outcome']=='PASS' else 6)
