"""Sequential native source-collider queries; source stages are never saved."""
import argparse
import json
import os
from pathlib import Path
import sys
import traceback


def classify_hits(hits,ignored,expected,z,tolerance=.002):
    excluded=[];source=[]
    for hit in hits:
        if any(hit['collider']==p or hit['collider'].startswith(p+'/') for p in ignored):excluded.append(hit)
        else:source.append(hit)
    source.sort(key=lambda h:h['distance']);first=source[0] if source else None
    passed=bool(first) and first['collider']==expected and abs(first['z']-z)<=tolerance
    return dict(passed=passed,hits=hits,excluded=excluded,nearest_source=first,
                reason=None if passed else 'EXPECTED_SOURCE_COLLIDER_OR_HEIGHT_NOT_HIT')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--request',type=Path,required=True);args=parser.parse_args()
    cfg=json.loads(args.request.read_text(encoding='utf-8'));out=args.request.parent
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from common_core.identity import sha256_file
    from common_core.manifest import write_json_new
    for name in ['cache','data','shadercache','drivercache','texturecache','optix']:(out/name).mkdir()
    os.environ['OPTIX_CACHE_PATH']=str(out/'optix');app=None;results=[];exception=None
    try:
        from isaacsim import SimulationApp
        app=SimulationApp(dict(headless=True,disable_viewport_updates=True,width=320,height=240,renderer='Minimal',multi_gpu=False,
            extra_args=['--/UJITSO/enabled=false','--/UJITSO/datastore/allowHubDataStore=false','--/app/settings/persistent=false',
                '--/app/exts/registryEnabled=false','--/app/window/enabled=false','--/log/file='+str(out/'isaac.log'),
                '--/app/userConfigPath='+str(out/'user.config.json'),'--/app/tokens/cache='+str(out/'cache'),
                '--/app/tokens/data='+str(out/'data'),'--/rtx/shaderDb/cachePath='+str(out/'shadercache'),
                '--/rtx/shaderDb/driverCachePath='+str(out/'drivercache'),
                '--/rtx-transient/resourcemanager/localTextureCachePath='+str(out/'texturecache')]))
        import omni.usd
        import omni.timeline
        from omni.physx import get_physx_scene_query_interface
        from pxr import UsdPhysics,PhysxSchema
        ctx=omni.usd.get_context();timeline=omni.timeline.get_timeline_interface()
        for index,case in enumerate(cfg['cases']):
            for kind in ['scene','manifest']:
                if sha256_file(case[kind])!=case[kind+'_sha256']:raise ValueError('SUPPORT_INPUT_HASH_MISMATCH')
            timeline.pause()
            if not ctx.open_stage(case['scene']):raise RuntimeError('SUPPORT_STAGE_OPEN_FAILED')
            for _ in range(5):app.update()
            stage=ctx.get_stage();stage.SetEditTarget(stage.GetSessionLayer())
            for prim in stage.Traverse():
                if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                    UsdPhysics.RigidBodyAPI(prim).CreateKinematicEnabledAttr(True)
                    PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateEnableCCDAttr(False)
                if prim.IsA(UsdPhysics.Joint):UsdPhysics.Joint(prim).CreateJointEnabledAttr(False)
                if prim.IsA(UsdPhysics.Scene):
                    api=PhysxSchema.PhysxSceneAPI.Apply(prim);api.CreateEnableGPUDynamicsAttr(False);api.CreateBroadphaseTypeAttr('MBP')
            timeline.play()
            for _ in range(5):app.update()
            checks=[]
            for query in case['queries']:
                for x,y in query['points']:
                    hits=[]
                    def collect(hit):
                        hits.append(dict(collider=str(hit.collision),z=float(hit.position[2]),distance=float(hit.distance)));return True
                    get_physx_scene_query_interface().raycast_all((x,y,query['support_z']+.0005),(0,0,-1),.04,collect)
                    checks.append(dict(instance_id=query['instance_id'],point=[x,y],expected=query['expected_collider'],
                        **classify_hits(hits,case['ignored'],query['expected_collider'],query['support_z'])))
            timeline.pause();outcome='PASS' if checks and all(c['passed'] for c in checks) else 'FAIL'
            result=dict(execution='EXECUTED',outcome=outcome,test_expectation=case.get('expect_outcome','PASS'),
                manifest_sha256=case['manifest_sha256'],scene_sha256=case['scene_sha256'],target_state_digest=case['state_digest'],checks=checks,
                scope='native source collider rays at center and projected footprint samples; all bodies kinematic, joints disabled in unsaved session; not dynamics',source_saved=False)
            if sha256_file(case['scene'])!=case['scene_sha256']:raise ValueError('SUPPORT_SOURCE_SCENE_CHANGED')
            write_json_new(out/('case-'+str(index)+'.json'),result);results.append(result)
            print('SUPPORT_CASE',index,outcome,len(checks),flush=True)
    except BaseException:
        exception=traceback.format_exc();traceback.print_exc()
    finally:
        passed=not exception and len(results)==len(cfg['cases']) and all(r['outcome']==r['test_expectation'] for r in results)
        write_json_new(out/'result.json',dict(execution='EXECUTED',outcome='PASS' if passed else 'UNKNOWN' if exception else 'FAIL',
            worker_sha256=sha256_file(__file__),results=[dict(outcome=r['outcome'],expectation=r['test_expectation'],manifest_sha256=r['manifest_sha256']) for r in results],exception=exception,
            scope='fixture expectations including explicit negative cases; each individual outcome remains separate'))
        if app is not None:app.close(wait_for_replicator=False,exit_code=0 if passed else 1)


if __name__=='__main__':main()
