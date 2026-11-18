"""Actual passive full-room CPU PhysX diagnostic; source layers are never saved."""
import argparse,json,math,os,sys,traceback
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);a=p.parse_args()
    cfg=json.loads(a.request.read_text(encoding='utf-8-sig'));out=a.request.parent
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from library import ROOT,read,write,sha
    assert sha(cfg['scene'])==cfg['scene_sha256']
    for name in ['cache','data','shadercache','drivercache','texturecache','optix']:(out/name).mkdir()
    os.environ['OPTIX_CACHE_PATH']=str(out/'optix');app=None;error=None;report={}
    try:
        from isaacsim import SimulationApp
        app=SimulationApp(dict(headless=True,disable_viewport_updates=True,width=320,height=240,renderer='Minimal',multi_gpu=False,
            extra_args=['--/UJITSO/enabled=false','--/app/settings/persistent=false','--/app/exts/registryEnabled=false','--/app/window/enabled=false',
                '--/log/file='+str(out/'isaac.log'),'--/app/userConfigPath='+str(out/'user.config.json'),'--/app/tokens/cache='+str(out/'cache'),
                '--/app/tokens/data='+str(out/'data'),'--/rtx/shaderDb/cachePath='+str(out/'shadercache'),'--/rtx/shaderDb/driverCachePath='+str(out/'drivercache'),
                '--/rtx-transient/resourcemanager/localTextureCachePath='+str(out/'texturecache')]))
        import omni.usd,omni.timeline
        from pxr import Usd,UsdGeom,UsdPhysics,PhysxSchema,PhysicsSchemaTools,Gf
        from isaacsim.core.api import World
        from omni.physx import get_physx_interface,get_physx_simulation_interface
        import omni.physics.tensors as tensors
        from common_core.writer import set_world
        context=omni.usd.get_context();assert context.open_stage(cfg['scene'])
        for _ in range(5):app.update()
        stage=context.get_stage();stage.SetEditTarget(stage.GetSessionLayer());bodies=[];joints=[];physics=[];new_masses={}
        import random
        perturbations={};perturb_rng=random.Random(cfg.get('perturb_seed')) if cfg.get('perturb_seed') is not None else None
        from dynamic_preflight import prepare_generated,disable_empty_colliders
        preflight=prepare_generated(stage,cfg['generated_bodies']) if cfg['mode']!='authored' else {}
        preflight['disabled_invalid_empty_mesh_colliders']=disable_empty_colliders(stage) if cfg['mode']!='authored' else []
        support_repairs=[]
        for sid,path in cfg.get('support_colliders',{}).items():
            prim=stage.GetPrimAtPath(path);parent=prim;dynamic=False
            while parent and not parent.IsPseudoRoot():
                if parent.HasAPI(UsdPhysics.RigidBodyAPI) and UsdPhysics.RigidBodyAPI(parent).GetRigidBodyEnabledAttr().Get()!=False:dynamic=True
                parent=parent.GetParent()
            if prim and prim.IsA(UsdGeom.Mesh) and not dynamic:
                mesh=UsdPhysics.MeshCollisionAPI.Apply(prim);previous=mesh.GetApproximationAttr().Get();mesh.CreateApproximationAttr('none')
                support_repairs.append(dict(support_id=sid,prim=path,before=previous,after='none',reason='Static rigid furniture collider must match sampled source triangle surface'))
        preflight['support_collision_repairs']=support_repairs
        write(out/'physics_preflight.json',preflight)
        estimates={'electronics':.35,'bag':.8,'luggage':3.,'clothing':.25,'footwear':.45,'towel':.3,'paper':.015,'toiletry':.25,'food':.35}
        for prim in stage.Traverse():
            path=str(prim.GetPath())
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                api=UsdPhysics.RigidBodyAPI(prim);bodies.append(dict(prim=path,authored_enabled=api.GetRigidBodyEnabledAttr().Get(),authored_kinematic=api.GetKinematicEnabledAttr().Get()))
                if path in cfg['generated_bodies'] and cfg['mode']!='authored':
                    api.CreateRigidBodyEnabledAttr(True);api.CreateKinematicEnabledAttr(False)
                    record=cfg.get('generated_bodies',{}).get(path,{})
                    mass=estimates.get(record.get('category'),.25)
                    if record.get('name','').lower().find('stylus')>=0:mass=.025
                    if perturb_rng:
                        factor=perturb_rng.uniform(.8,1.2);mass*=factor
                        com=Gf.Vec3f(perturb_rng.uniform(-.001,.001),perturb_rng.uniform(-.001,.001),0)
                        bounds=UsdGeom.BBoxCache(0,['default']).ComputeUntransformedBound(prim).ComputeAlignedRange();center=(bounds.GetMin()+bounds.GetMax())/2
                        UsdPhysics.MassAPI.Apply(prim).CreateCenterOfMassAttr(Gf.Vec3f(*center)+com)
                        perturbations[path]=dict(mass_factor=factor,center_of_mass_offset_m=list(com))
                    UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
                    PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateDisableGravityAttr(False)
                    new_masses[path]=dict(mass_kg=mass,provenance='HEURISTIC_CATEGORY_ESTIMATE_NOT_CALIBRATED',proxy='SESSION_PREFLIGHT_COLLIDERS_SEE_PHYSICS_PREFLIGHT_JSON')
                elif cfg['mode']=='source_fixed_props_dynamic':api.CreateRigidBodyEnabledAttr(False)
            if prim.IsA(UsdPhysics.Joint):
                joints.append(path)
                if cfg['mode']=='source_fixed_props_dynamic':UsdPhysics.Joint(prim).CreateJointEnabledAttr(False)
            if prim.IsA(UsdPhysics.Scene):physics.append(path)
        assert len(physics)==1,physics
        scene=UsdPhysics.Scene(stage.GetPrimAtPath(physics[0]));scene.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));scene.CreateGravityMagnitudeAttr(9.81)
        api=PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim());api.CreateEnableGPUDynamicsAttr(False);api.CreateBroadphaseTypeAttr('MBP');api.CreateEnableStabilizationAttr(True)
        before=out/'runtime_initial_opinions.usda';stage.GetSessionLayer().Export(str(before))
        initial=Usd.Stage.CreateNew(str(out/'runtime_initial.usda'));initial.GetRootLayer().subLayerPaths=[os.path.relpath(before,out).replace('\\','/'),os.path.relpath(cfg['scene'],out).replace('\\','/')]
        UsdGeom.SetStageUpAxis(initial,'Z');UsdGeom.SetStageMetersPerUnit(initial,1);initial.GetRootLayer().Save()
        errors=[];contacts={};callbacks=[];dts=[]
        def contact(headers,data):
            try:
                for h in headers:
                    paths=sorted([str(PhysicsSchemaTools.intToSdfPath(h.collider0)),str(PhysicsSchemaTools.intToSdfPath(h.collider1))]);key=' | '.join(paths)
                    row=contacts.setdefault(key,dict(colliders=paths,events=0,points=0,min_separation_m=0.))
                    row['events']+=1;row['points']+=int(h.num_contact_data)
                    for i in range(h.contact_data_offset,h.contact_data_offset+h.num_contact_data):row['min_separation_m']=min(row['min_separation_m'],float(data[i].separation))
            except Exception:callbacks.append(traceback.format_exc())
        active=[];cache=UsdGeom.BBoxCache(0,['default','render','proxy']);initial_boxes={}
        for b in bodies:
            prim=stage.GetPrimAtPath(b['prim']);body=UsdPhysics.RigidBodyAPI(prim)
            if body.GetRigidBodyEnabledAttr().Get() and not body.GetKinematicEnabledAttr().Get():
                active.append(b['prim']);PhysxSchema.PhysxContactReportAPI.Apply(prim).CreateThresholdAttr(0)
                r=cache.ComputeWorldBound(prim).ComputeAlignedRange();initial_boxes[b['prim']]=[list(r.GetMin()),list(r.GetMax())]
        subscriptions=[get_physx_simulation_interface().subscribe_contact_report_events(contact),get_physx_interface().subscribe_physics_step_events(lambda dt:dts.append(float(dt))),
            get_physx_interface().get_error_event_stream().create_subscription_to_pop(lambda e:errors.append(dict(type=int(e.type),payload=str(e.payload))) if len(errors)<200 else None)]
        world=World(physics_dt=1/120,rendering_dt=1/120,stage_units_in_meters=1,physics_prim_path=physics[0],
            sim_params={'use_gpu_pipeline':False,'use_fabric':False},device='cpu');world.get_physics_context().enable_fabric(False);world.reset()
        simulation=tensors.create_simulation_view('numpy',stage_id=context.get_stage_id(),backend='physx');simulation.set_subspace_roots('/')
        views={};missing=[]
        for path in active:
            view=simulation.create_rigid_body_view(path)
            if view.count==1:views[path]=view
            else:missing.append(dict(prim=path,native_count=view.count))
        assert views,'NO_REGISTERED_DYNAMIC_BODIES'
        trajectory={path:[] for path in views};relative={}
        def pose_matrix(pose):
            m=Gf.Matrix4d(1).SetRotate(Gf.Rotation(Gf.Quatd(pose[6],Gf.Vec3d(*pose[3:6]))));m.SetTranslateOnly(Gf.Vec3d(*pose[:3]));return m
        initial_world={path:UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(0) for path in views}
        initial_physics={}
        for path,view in views.items():
            matrix=pose_matrix(view.get_transforms().copy()[0].astype(float).tolist());inverse=matrix.GetInverse();lo,hi=initial_boxes[path]
            initial_physics[path]=matrix
            relative[path]=[inverse.Transform(Gf.Vec3d(x,y,z)) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]]
        def sample(n):
            for path,view in views.items():
                pose=view.get_transforms().copy()[0].astype(float).tolist();velocity=view.get_velocities().copy()[0].astype(float).tolist()
                assert all(math.isfinite(v) for v in pose+velocity),'NONFINITE_STATE:'+path
                matrix=pose_matrix(pose);points=[matrix.Transform(v) for v in relative[path]]
                trajectory[path].append(dict(step=n,time_s=n/120,pose_xyzw=pose,velocity=velocity,bottom_z=min(v[2] for v in points)))
        init=len(dts);sample(0);steps=round(cfg['seconds']*120)
        for n in range(1,steps+1):
            world.step(render=False)
            if n%12==0 or n==steps:sample(n)
            if n%240==0:print('FULL_ROOM_DYNAMIC_STEP',n,'/',steps,'bodies',len(views),flush=True)
        measured=dts[init:];issues=[];summary=[]
        norm=lambda v:math.sqrt(sum(x*x for x in v))
        for path,samples in trajectory.items():
            initial_pose=samples[0]['pose_xyzw'];last=samples[-1];distance=max(math.dist(s['pose_xyzw'][:3],initial_pose[:3]) for s in samples)
            speed=max(norm(s['velocity'][:3]) for s in samples);bottom=min(s['bottom_z'] for s in samples)
            row=dict(prim=path,generated=path.startswith('/CommonCore/'),max_displacement_m=distance,max_linear_speed_mps=speed,min_bottom_z=bottom,
                final_linear_speed_mps=norm(last['velocity'][:3]),final_angular_speed_radps=norm(last['velocity'][3:]),final_position=last['pose_xyzw'][:3])
            flags=[]
            if bottom<-.2:flags.append('FELL_BELOW_ROOM_FLOOR')
            if speed>15 or distance>3:flags.append('LARGE_EXCURSION_OR_SPEED')
            if row['final_linear_speed_mps']>.03 or row['final_angular_speed_radps']>.2:flags.append('NOT_SETTLED_AT_END')
            if row['generated'] and last['pose_xyzw'][2]<initial_pose[2]-.12:flags.append('DROPPED_FROM_INITIAL_SUPPORT_HEIGHT')
            if flags:issues.append(dict(**row,issues=flags))
            summary.append(row)
        final_matrices={p:[[float(v) for v in row] for row in initial_world[p]*initial_physics[p].GetInverse()*pose_matrix(trajectory[p][-1]['pose_xyzw'])] for p in views}
        write(out/'final_world_matrices.json',final_matrices)
        for name,freeze in [('runtime_final_dynamic.usda',False),('runtime_final_frozen.usda',True)]:
            frozen=Usd.Stage.CreateNew(str(out/name));frozen.GetRootLayer().subLayerPaths=['runtime_initial.usda']
            UsdGeom.SetStageUpAxis(frozen,'Z');UsdGeom.SetStageMetersPerUnit(frozen,1)
            for path in sorted(views,key=lambda x:x.count('/')):
                prim=frozen.OverridePrim(path);set_world(prim,final_matrices[path]);UsdPhysics.RigidBodyAPI(prim).CreateKinematicEnabledAttr(freeze)
                UsdPhysics.RigidBodyAPI(prim).CreateVelocityAttr(Gf.Vec3f(0));UsdPhysics.RigidBodyAPI(prim).CreateAngularVelocityAttr(Gf.Vec3f(0))
            frozen.GetRootLayer().Save()
        write(out/'trajectory.json',dict(trajectories=trajectory,physical_masses={p:v.get_masses().copy().astype(float).tolist() for p,v in views.items()}))
        world.stop()
        healthy=not errors and not callbacks and len(measured)==steps and all(abs(t-1/120)<1e-6 for t in measured)
        report=dict(execution='COMPLETED',outcome='DIAGNOSTIC_PASS' if healthy and not issues and not missing else 'ISSUES_FOUND',simulation_health='PASS' if healthy else 'FAIL',
            seconds=cfg['seconds'],native_steps=len(measured),dt=1/120,mode=cfg['mode'],usd_rigid_bodies=len(bodies),active_usd_bodies=len(active),registered_dynamic_bodies=len(views),missing=missing,
            authored_joints=len(joints),joints_disabled_for_isolation=cfg['mode']=='source_fixed_props_dynamic',issues=issues,body_summary=summary,contacts=list(contacts.values()),
            physx_errors=errors,callback_errors=callbacks,new_mass_estimates=new_masses,source_saved=False,source_sha256=cfg['scene_sha256'],
            worker_sha256=sha(__file__),perturb_seed=cfg.get('perturb_seed'),perturbations=perturbations,limits=['Diagnostic only; heuristic masses and static AABB asset proxies are not calibrated dynamic asset qualifications','No flexible-body deformation or robot manipulation qualification'])
    except BaseException:
        error=traceback.format_exc();traceback.print_exc();report=dict(execution='FAILED',outcome='ERROR',error=error,source_saved=False)
    finally:
        assert sha(cfg['scene'])==cfg['scene_sha256']
        write(out/'result.json',report)
        if app:app.close(wait_for_replicator=False,exit_code=1 if error else 0)

if __name__=='__main__':main()
