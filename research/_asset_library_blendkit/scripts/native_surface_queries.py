"""Native triangle support measurement in an unsaved static session only."""
import argparse,json,os,sys,traceback
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);args=p.parse_args()
    cfg=json.loads(args.request.read_text(encoding='utf-8-sig'));out=args.request.parent
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from library import read,write,sha
    for name in ['cache','data','shadercache','drivercache','texturecache','optix']:(out/name).mkdir(exist_ok=False)
    os.environ['OPTIX_CACHE_PATH']=str(out/'optix');app=None;results=[];error=None
    try:
        from isaacsim import SimulationApp
        app=SimulationApp(dict(headless=True,disable_viewport_updates=True,width=320,height=240,renderer='Minimal',multi_gpu=False,
            extra_args=['--/UJITSO/enabled=false','--/app/settings/persistent=false','--/app/exts/registryEnabled=false','--/app/window/enabled=false',
                '--/log/file='+str(out/'isaac.log'),'--/app/userConfigPath='+str(out/'user.config.json'),'--/app/tokens/cache='+str(out/'cache'),
                '--/app/tokens/data='+str(out/'data'),'--/rtx/shaderDb/cachePath='+str(out/'shadercache'),'--/rtx/shaderDb/driverCachePath='+str(out/'drivercache'),
                '--/rtx-transient/resourcemanager/localTextureCachePath='+str(out/'texturecache')]))
        import omni.usd,omni.timeline
        from omni.physx import get_physx_scene_query_interface
        from pxr import UsdPhysics,PhysxSchema
        context=omni.usd.get_context();timeline=omni.timeline.get_timeline_interface()
        for index,case in enumerate(cfg['cases']):
            for key in ['scene','manifest']:assert sha(case[key])==case[key+'_sha256']
            timeline.pause();assert context.open_stage(case['scene'])
            for _ in range(5):app.update()
            stage=context.get_stage();stage.SetEditTarget(stage.GetSessionLayer())
            for prim in stage.Traverse():
                if prim.HasAPI(UsdPhysics.RigidBodyAPI):UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
                if prim.IsA(UsdPhysics.Joint):UsdPhysics.Joint(prim).CreateJointEnabledAttr(False)
                if prim.IsA(UsdPhysics.Scene):
                    api=PhysxSchema.PhysxSceneAPI.Apply(prim);api.CreateEnableGPUDynamicsAttr(False);api.CreateBroadphaseTypeAttr('MBP')
            changed=[]
            for path in sorted({q['expected'] for q in case['queries']}):
                prim=stage.GetPrimAtPath(path);assert prim and prim.HasAPI(UsdPhysics.CollisionAPI)
                mesh=UsdPhysics.MeshCollisionAPI.Apply(prim);before=mesh.GetApproximationAttr().Get()
                mesh.CreateApproximationAttr('none');changed.append(dict(prim=path,original_approximation=before,session_approximation='none'))
            timeline.play()
            for _ in range(8):app.update()
            checks=[]
            for query in case['queries']:
                for point,z in zip(query['points'],query['heights']):
                    x,y=point;hits=[]
                    def collect(hit):
                        path=str(hit.collision)
                        if not path.startswith('/CommonCore/'):
                            hits.append(dict(collider=path,z=float(hit.position[2]),distance=float(hit.distance)))
                        return True
                    get_physx_scene_query_interface().raycast_all((x,y,z+.003),(0,0,-1),.02,collect)
                    hits.sort(key=lambda h:h['distance']);first=hits[0] if hits else None
                    passed=bool(first) and first['collider']==query['expected'] and abs(first['z']-z)<=.002
                    checks.append(dict(instance_id=query['instance_id'],support_id=query['support_id'],point=point,expected_z=z,
                        passed=passed,nearest=first))
            timeline.pause();assert sha(case['scene'])==case['scene_sha256']
            report=dict(outcome='PASS' if checks and all(c['passed'] for c in checks) else 'FAIL',checks=checks,session_collider_adaptations=changed,
                manifest_sha256=case['manifest_sha256'],scene_sha256=case['scene_sha256'],source_saved=False,
                scope='Actual native rays against exact unchanged source triangle meshes, approximation=none in unsaved session; all bodies static. Original approximation/dynamics not qualified')
            write(out/('case-'+str(index)+'.json'),report);results.append(dict(outcome=report['outcome'],checks=len(checks),failed=sum(not c['passed'] for c in checks)))
            print('NATIVE_MEASURED_SURFACE',index,results[-1],flush=True)
    except BaseException:
        error=traceback.format_exc();traceback.print_exc()
    finally:
        passed=not error and len(results)==len(cfg['cases']) and all(r['outcome']=='PASS' for r in results)
        write(out/'result.json',dict(outcome='PASS' if passed else 'FAIL',results=results,error=error,worker_sha256=sha(__file__),source_saved=False))
        if app:app.close(wait_for_replicator=False,exit_code=0 if passed else 1)

if __name__=='__main__':main()
