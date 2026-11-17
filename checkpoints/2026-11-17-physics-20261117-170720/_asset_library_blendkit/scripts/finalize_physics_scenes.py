"""Export simulator-derived poses, replay the same physics opinions, and prepare captures."""
from generate_surface_scenes import *
from check_settled_trajectory import check
from common_core.identity import state_digest
from common_core.replay import signatures
from pxr import UsdUtils
from dynamic_preflight import disable_empty_colliders
import os

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--tag',default='physics_settled_a001');p.add_argument('--resume',action='store_true');a=p.parse_args()
    out=ROOT/'runs'/a.tag;out.mkdir(exist_ok=a.resume);cases=[];render=[]
    old_cameras=read(ROOT/'runs/measured_surfaces_a002/render_batch.json')['cases'][0]['cameras']
    from run_surface_pipeline import corrected_camera_batch
    camera_batch=corrected_camera_batch(dict(cases=[dict(manifest='unused',cameras=old_cameras)]))
    cameras=camera_batch['cases'][0]['cameras']
    for case in read(a.run/'cases.json')['cases']:
        if case.get('physics_outcome')!='PASS':raise ValueError('UNRESOLVED_CASE:'+str(case))
        saved=out/(case['level']+str(case['seed']))/'case.json'
        if saved.exists() and a.resume:
            existing=read(saved);assert existing['accepted']==case['accepted'];assert sha(existing['scene'])==read(existing['manifest'])['scene']['sha256'];cases.append(existing)
            render.append(dict(manifest=existing['manifest'],cameras={v:cameras[v] for v in ['overview','floor_foot','bed_surface','pillow_left_detail','chair_seat']}));continue
        attempt=Path(case['accepted']);inputs=load_inputs(Path(case['config']),'hotel705');surfaces=Surfaces(inputs.profile,inputs.bindings)
        strict=check(attempt,surfaces);assert strict['outcome']=='PASS',strict['issues']
        folder=out/(case['level']+str(case['seed']));folder.mkdir()
        original=read(attempt/'manifest.json');objects=copy.deepcopy(original['objects']);matrices=read(attempt/'dynamics/final_world_matrices.json')
        for obj in objects:
            matrix=matrices[object_prim(obj)];before=Gf.Matrix4d(*[v for row in obj['effective']['world_matrix'] for v in row]);after=Gf.Matrix4d(*[v for row in matrix for v in row])
            assert abs(before.GetDeterminant()-after.GetDeterminant())<1e-6,'SIMULATED_SCALE_CHANGED'
            obj['effective']['world_matrix']=matrix;obj['after']=copy.deepcopy(obj['effective'])
        scene=folder/'scene.usda';stage=write_scene(scene,inputs,dict(objects=objects));opinions=attempt/'dynamics/runtime_initial_opinions.usda'
        stage.GetRootLayer().subLayerPaths.insert(0,os.path.relpath(opinions,folder).replace('\\','/'));stage.GetRootLayer().Save()
        empty_colliders=disable_empty_colliders(stage);stage.GetRootLayer().Save()
        cache=UsdGeom.BBoxCache(0,['default','render','proxy'])
        for obj in objects:obj['expected_bounds']=bounds(stage.GetPrimAtPath(object_prim(obj)),cache)
        plan=dict(seed=case['seed'],scenario='STAYOVER',level=case['level'],targets=original['targets'],requests=original['requests'],budgets=inputs.policy['budgets'])
        manifest=build_manifest(inputs,plan,dict(objects=objects),scene,a.tag)
        manifest['limits']=['CONTROLLED_LOCAL_NO_DISTRIBUTION','Experimental rigid surrogate simulation; no calibrated dynamics, flexible deformation or robot manipulation qualification']
        write(folder/'strict_stability.json',strict)
        for obj in objects:
            lo,hi=obj['expected_bounds'];obj['footprint']=rectangle(lo[:2],hi[:2])
        manifest['objects']=copy.deepcopy(objects);manifest['scene']['state_digest']=state_digest(manifest)
        manifest['environment']['scope']='Final poses from full-room CPU PhysX,30s,3600steps at120Hz; independent static geometry clearance is initial-proposal evidence'
        unresolved=UsdUtils.ComputeAllDependencies(str(scene))[2];assert not unresolved,list(unresolved)
        # Core replay reconstructs effective matrices without RNG. Add exactly the
        # pinned collider/material opinions, then compare complete generated content.
        replay=replay_manifest(manifest,folder/'replay',inputs)
        replay_stage=Usd.Stage.Open(str(folder/'replay/scene.usda'))
        replay_stage.GetRootLayer().subLayerPaths.insert(0,os.path.relpath(opinions,folder/'replay').replace('\\','/'));replay_stage.GetRootLayer().Save()
        assert disable_empty_colliders(replay_stage)==empty_colliders;replay_stage.GetRootLayer().Save()
        left=signatures(stage,objects);right=signatures(replay_stage,objects)
        errors=[key for key in left if left[key]['content']!=right[key]['content'] or max(abs(left[key]['matrix'][i][j]-right[key]['matrix'][i][j]) for i in range(4) for j in range(4))>1e-8]
        assert not errors,errors
        replay.update(outcome='PASS',physics_opinions_sha256=sha(opinions),generated_content_and_matrix_errors=errors,scope='RNG-free settled effective pose replay plus pinned collider/material opinions; no assertion of bitwise dynamics reproducibility')
        write(folder/'replay.json',replay)
        native=read(attempt/'dynamics/result.json')
        write(folder/'physics_evidence.json',dict(**strict,proposal_manifest=str(attempt/'manifest.json'),proposal_manifest_sha256=sha(attempt/'manifest.json'),native_result=str(attempt/'dynamics/result.json'),native_steps=native['native_steps'],registered_dynamic_bodies=native['registered_dynamic_bodies'],authored_joints=native['authored_joints'],source_saved=False,final_matrices_sha256=sha(attempt/'dynamics/final_world_matrices.json')))
        write(folder/'integrity.json',dict(outcome='PASS',unresolved=[],scene_sha256=sha(scene),physics_opinions_sha256=sha(opinions),scope='USD dependency closure and pinned source physics preparation'))
        write(folder/'initial_static.json',read(attempt/'static.json'))
        for kind in ['physics_evidence','integrity','replay']:
            manifest['evidence_refs'].append(dict(kind=kind,uri=kind+'.json',sha256=sha(folder/(kind+'.json')),execution='EXECUTED',outcome='PASS',scope='Controlled local simulated settled scene',target_state_digest=manifest['scene']['state_digest'],producer_identity=dict(code_hash=manifest['inputs']['code_hash'])))
        seal_manifest(manifest,folder/'manifest.json')
        dynamic=Usd.Stage.CreateNew(str(folder/'scene_dynamic.usda'));dynamic.GetRootLayer().subLayerPaths=['scene.usda']
        UsdGeom.SetStageUpAxis(dynamic,'Z');UsdGeom.SetStageMetersPerUnit(dynamic,1)
        for obj in objects:UsdPhysics.RigidBodyAPI(dynamic.OverridePrim(object_prim(obj))).CreateKinematicEnabledAttr(False)
        dynamic.GetRootLayer().Save()
        final_case={**case,'manifest':str(folder/'manifest.json'),'scene':str(scene),'dynamic_scene':str(folder/'scene_dynamic.usda'),'physics_evidence':str(folder/'physics_evidence.json'),'unique_assets':len({o['asset_id'] for o in objects}),'surface_counts':dict(Counter(o['effective']['support_id'] for o in objects))}
        write(folder/'case.json',final_case);cases.append(final_case)
        write(folder/'case.json',cases[-1])
        render.append(dict(manifest=str(folder/'manifest.json'),cameras={v:cameras[v] for v in ['overview','floor_foot','bed_surface','pillow_left_detail','chair_seat']}))
    write(out/'cases.json',dict(cases=cases));write(out/'render_batch.json',dict(cases=render));print('SETTLED_EXPORT',len(cases),str(out),flush=True)

if __name__=='__main__':main()
