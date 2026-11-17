"""Fresh final artifact checks; physics qualification is scoped to these exact cases."""
from generate_surface_scenes import *
from common_core.replay import load_manifest,signatures
from pxr import UsdUtils
from check_settled_trajectory import check
import subprocess,ast

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();cases=read(a.run/'cases.json')['cases'];checks=[]
    for case in cases:
        inputs=load_inputs(Path(case['config']),'hotel705');m=load_manifest(Path(case['manifest']),inputs);stage=Usd.Stage.Open(case['scene']);dynamic=Usd.Stage.Open(case['dynamic_scene']);cache=UsdGeom.BBoxCache(0,['default','render','proxy'])
        strict=check(Path(case['accepted']),Surfaces(inputs.profile,inputs.bindings));assert strict['outcome']=='PASS',strict
        assert case['count']==len(m['objects']);assert read(Path(case['manifest']).parent/'physics_evidence.json')['outcome']=='PASS'
        native=read(Path(case['accepted'])/'dynamics/result.json');surface=Surfaces(inputs.profile,inputs.bindings);support_checks=[]
        for obj in m['objects']:
            path=object_prim(obj);root=stage.GetPrimAtPath(path)
            actual=rows(UsdGeom.Xformable(root).ComputeLocalToWorldTransform(0));assert max(abs(actual[i][j]-obj['effective']['world_matrix'][i][j]) for i in range(4) for j in range(4))<1e-8
            measured=bounds(root,cache);assert max(abs(measured[i][j]-obj['expected_bounds'][i][j]) for i in range(2) for j in range(3))<1e-7
            assert UsdPhysics.RigidBodyAPI(root).GetKinematicEnabledAttr().Get() is True
            assert UsdPhysics.RigidBodyAPI(dynamic.GetPrimAtPath(path)).GetKinematicEnabledAttr().Get() is False
            assert not any(p!=root and p.HasAPI(UsdPhysics.RigidBodyAPI) for p in Usd.PrimRange(root))
            assert any(p.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()!=False for p in Usd.PrimRange(root))
            expected=surface.specs[obj['effective']['support_id']]['collider']
            contacts=[c for c in native['contacts'] if expected in c['colliders'] and any(q.startswith(path+'/') for q in c['colliders']) and c['points']>0]
            assert contacts,('NO_NATIVE_EXPECTED_SUPPORT_CONTACT',path,expected)
            support_checks.append(dict(instance_id=obj['instance_id'],support_id=obj['effective']['support_id'],expected_collider=expected,observed_contacts=contacts))
            # A rotated hierarchy's aligned box includes empty corners. Check actual
            # rendered mesh vertices against the room floor, not that conservative box.
            if obj['effective']['support_id'].startswith('floor_'):
                gaps=[]
                for prim in Usd.PrimRange(root):
                    if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
                    matrix=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
                    for v in UsdGeom.Mesh(prim).GetPointsAttr().Get():
                        point=matrix.Transform(Gf.Vec3d(v));height=surface.meshes[obj['effective']['support_id']].height(point[0],point[1])
                        if height is not None:gaps.append(point[2]-height)
                assert gaps and min(gaps)>-.002,('ACTUAL_VISUAL_GEOMETRY_BELOW_FLOOR',path,min(gaps) if gaps else None)
                support_checks[-1]['minimum_actual_mesh_floor_gap_m']=min(gaps)
        write(Path(case['manifest']).parent/'native_support.json',dict(outcome='PASS',checks=support_checks,native_result_sha256=sha(Path(case['accepted'])/'dynamics/result.json'),scope='Actual native PhysX expected-support contact reports during30s dynamics; final2s stability and COM-region retention checked separately; not a soft support deformation qualification'))
        assert not UsdUtils.ComputeAllDependencies(case['scene'])[2]
        replay=Usd.Stage.Open(str(Path(case['manifest']).parent/'replay/scene.usda'))
        actual=signatures(stage,m['objects']);other=signatures(replay,m['objects']);assert actual==other
        checks.append(dict(level=case['level'],seed=case['seed'],count=case['count'],outcome='PASS',manifest_sha256=sha(case['manifest']),scene_sha256=sha(case['scene']),dynamic_scene_sha256=sha(case['dynamic_scene'])))
    for name in ['dynamic_preflight.py','room_dynamic_worker.py','launch_room_dynamics.py','run_physics_guided_scenes.py','finalize_physics_scenes.py','run_density_physics_pipeline.py','report_physics_scenes.py']:
        ast.parse((ROOT/'scripts'/name).read_text(encoding='utf-8-sig'))
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_*.py'],capture_output=True,text=True);assert tests.returncode==0,tests.stdout+tests.stderr
    protected=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/verify_protected.py')],capture_output=True,text=True);assert protected.returncode==0,protected.stdout+protected.stderr
    write(a.run/'verification.json',dict(outcome='PASS',cases=checks,tests=tests.stderr,protected=read(ROOT/'reports/protected_verification.json'),scope='Exact six candidate cases: simulated rigid surrogate evidence, pinned effective-pose replay, USD closure/body structure, regression tests and protected hashes; no public rights or deformable qualification'))
    print('PHYSICS_ARTIFACT_VERIFICATION_PASS',len(checks))

if __name__=='__main__':main()
