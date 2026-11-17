"""Exact-scope CPU PhysX worker adapted from pinned Hotel contact/tensor probes.

All physical opinions live in an unsaved session layer. Never run at import.
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import traceback


def proxy_supported(kind):
    return kind in ('box','cylinder')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',type=Path,required=True);args=parser.parse_args()
    cfg=json.loads(args.case.read_text(encoding='utf-8'));out=args.case.parent
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from common_core.identity import sha256_file
    from common_core.manifest import write_json_new
    for key in ['scene','manifest']:
        if sha256_file(cfg[key])!=cfg[key+'_sha256']:raise ValueError('NATIVE_INPUT_HASH_MISMATCH')
    if not cfg['targets']:raise ValueError('NATIVE_TARGETS_EMPTY')
    if any(not proxy_supported(t['proxy_kind']) for t in cfg['targets']):raise ValueError('NATIVE_PROXY_UNSUPPORTED')
    for name in ['cache','data','shadercache','drivercache','texturecache','optix']:(out/name).mkdir()
    os.environ['OPTIX_CACHE_PATH']=str(out/'optix');app=None;report=dict(execution='EXECUTED',outcome='UNKNOWN',scope=cfg['scope'])
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
        import omni.physics.tensors as tensors
        from omni.physx import get_physx_interface,get_physx_simulation_interface,get_physx_scene_query_interface
        from isaacsim.core.api import World
        from pxr import Usd,UsdGeom,UsdPhysics,Gf,PhysxSchema,PhysicsSchemaTools
        from common_core.adapters import footprint_supported
        ctx=omni.usd.get_context()
        if not ctx.open_stage(cfg['scene']):raise RuntimeError('NATIVE_STAGE_OPEN_FAILED')
        for _ in range(5):app.update()
        stage=ctx.get_stage();stage.SetEditTarget(stage.GetSessionLayer());targets={t['prim']:t for t in cfg['targets']}
        frozen=0;joints=0;scenes=[]
        for prim in stage.Traverse():
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                UsdPhysics.RigidBodyAPI(prim).CreateKinematicEnabledAttr(str(prim.GetPath()) not in targets)
                PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateEnableCCDAttr(False)
                if str(prim.GetPath()) not in targets:frozen+=1
            if prim.IsA(UsdPhysics.Joint):UsdPhysics.Joint(prim).CreateJointEnabledAttr(False);joints+=1
            if prim.IsA(UsdPhysics.Scene):scenes.append(str(prim.GetPath()))
        if len(scenes)>1:raise ValueError('MULTIPLE_PHYSICS_SCENES')
        physics_path=scenes[0] if scenes else '/CommonCoreRuntime/PhysicsScene';physics=UsdPhysics.Scene.Define(stage,physics_path)
        physics.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));physics.CreateGravityMagnitudeAttr(9.81)
        api=PhysxSchema.PhysxSceneAPI.Apply(physics.GetPrim());api.CreateEnableGPUDynamicsAttr(False);api.CreateBroadphaseTypeAttr('MBP')
        relative={};local_extents={};initial_expected={};preserved_instance_colliders=[]
        for path,target in targets.items():
            prim=stage.GetPrimAtPath(path);shape=stage.GetPrimAtPath(target['shape'])
            if not prim or not shape or not shape.HasAPI(UsdPhysics.CollisionAPI):raise ValueError('TARGET_COLLIDER_MISSING')
            if shape.GetTypeName() not in ('Cube','Cylinder'):raise ValueError('UNSUPPORTED_NATIVE_SHAPE')
            PhysxSchema.PhysxContactReportAPI.Apply(prim).CreateThresholdAttr(0)
            PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateDisableGravityAttr(False)
            PhysxSchema.PhysxRigidBodyAPI.Apply(prim).CreateEnableCCDAttr(False)
            for collider in [shape,stage.GetPrimAtPath(target['support_collider'])]:
                if not collider or not collider.HasAPI(UsdPhysics.CollisionAPI):raise ValueError('EXPECTED_SOURCE_COLLIDER_MISSING')
                if collider.IsInstanceProxy():
                    preserved_instance_colliders.append(str(collider.GetPath()));continue
                api=PhysxSchema.PhysxCollisionAPI.Apply(collider);api.CreateContactOffsetAttr(.001);api.CreateRestOffsetAttr(0)
            body_world=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
            relative[path]=UsdGeom.Xformable(shape).ComputeLocalToWorldTransform(0)*body_world.GetInverse()
            local_extents[path]=UsdGeom.Boundable(shape).ComputeExtent(Usd.TimeCode.Default())
            initial_expected[path]=body_world
        contacts={};dts=[];callback_errors=[];physx_errors=[];step={'n':0}
        def contact(headers,data):
            try:
                for header in headers:
                    paths=[str(PhysicsSchemaTools.intToSdfPath(x)) for x in [header.collider0,header.collider1]]
                    if not any(t['shape'] in paths for t in targets.values()):continue
                    key='|'.join(sorted(paths));record=contacts.setdefault(key,dict(colliders=paths,events=0,points=0,minimum_separation_m=0.))
                    record['events']+=1
                    for index in range(header.contact_data_offset,header.contact_data_offset+header.num_contact_data):
                        record['points']+=1;record['minimum_separation_m']=min(record['minimum_separation_m'],float(data[index].separation))
            except Exception:callback_errors.append(traceback.format_exc())
        subscriptions=[get_physx_simulation_interface().subscribe_contact_report_events(contact),
            get_physx_interface().subscribe_physics_step_events(lambda dt:dts.append(float(dt))),
            get_physx_interface().get_error_event_stream().create_subscription_to_pop(lambda e:physx_errors.append(dict(type=int(e.type),payload=str(e.payload))))]
        world=World(physics_dt=1/120,rendering_dt=1/120,stage_units_in_meters=1,physics_prim_path=physics_path,
            sim_params={'use_gpu_pipeline':False,'use_fabric':False},device='cpu')
        world.get_physics_context().enable_fabric(False);world.reset()
        simulation=tensors.create_simulation_view('numpy',stage_id=ctx.get_stage_id(),backend='physx');simulation.set_subspace_roots('/')
        bodies={path:simulation.create_rigid_body_view(path) for path in targets}
        if any(body.count!=1 or body.max_shapes!=1 for body in bodies.values()):raise ValueError('NATIVE_BODY_SHAPE_COUNT')
        physical_properties={path:dict(mass_kg=body.get_masses().copy().astype(float).tolist(),
            inertia=body.get_inertias().copy().astype(float).tolist(),provenance='ACTUAL_NATIVE_TENSOR_VALUES; defaults are not calibrated measurements')
            for path,body in bodies.items()}
        def sample(path,n):
            pose=bodies[path].get_transforms().copy()[0].astype(float).tolist();velocity=bodies[path].get_velocities().copy()[0].astype(float).tolist()
            if not all(math.isfinite(v) for v in pose+velocity):raise ValueError('NONFINITE_NATIVE_STATE')
            matrix=Gf.Matrix4d(1).SetRotate(Gf.Rotation(Gf.Quatd(pose[6],Gf.Vec3d(*pose[3:6]))));matrix.SetTranslateOnly(Gf.Vec3d(*pose[:3]))
            collider=relative[path]*matrix;lo,hi=local_extents[path]
            points=[list(collider.Transform(Gf.Vec3d(x,y,z))) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]]
            footprint=[[p[0],p[1]] for p in points]
            return dict(step=n,pose_xyzw=pose,velocity=velocity,bottom_z=min(p[2] for p in points),
                        footprint_retained=footprint_supported(targets[path]['support'],footprint,0.))
        init=len(dts);initial_contacts=list(contacts.values());contacts.clear();trajectory={path:[sample(path,0)] for path in targets}
        for n in range(1,241):
            step['n']=n;world.step(render=False)
            for path in targets:trajectory[path].append(sample(path,n))
        checks={};speed=lambda v:math.sqrt(sum(x*x for x in v))
        for path,target in targets.items():
            samples=trajectory[path];expected=[c for c in contacts.values() if target['shape'] in c['colliders'] and target['support_collider'] in c['colliders']]
            unexpected=[c for c in contacts.values() if target['shape'] in c['colliders'] and target['support_collider'] not in c['colliders']]
            q=initial_expected[path].ExtractRotationQuat();expected_q=[*q.GetImaginary(),q.GetReal()];actual_q=samples[0]['pose_xyzw'][3:]
            angle=math.degrees(2*math.acos(min(1.,abs(sum(a*b for a,b in zip(expected_q,actual_q))))))
            checks[path]=dict(expected_support_contact=any(c['points'] for c in expected),no_unexpected_contacts=not unexpected,
                footprint_retained=all(s['footprint_retained'] for s in samples),penetration_under_3mm=min(s['bottom_z'] for s in samples)>=target['support']['z']-.003,
                displacement_under_3cm=max(math.dist(s['pose_xyzw'][:3],samples[0]['pose_xyzw'][:3]) for s in samples)<.03,
                initial_position_matches=math.dist(samples[0]['pose_xyzw'][:3],list(initial_expected[path].ExtractTranslation()))<=.003,
                initial_angle_matches=angle<=.1,settled_last_30=all(speed(s['velocity'][:3])<.01 and speed(s['velocity'][3:])<.1 for s in samples[-30:]))
        measured=dts[init:];common=dict(native_steps=len(measured)==240,native_120hz=all(abs(dt-1/120)<1e-6 for dt in measured),
            callbacks_clean=not callback_errors,physx_errors_clean=not physx_errors,all_target_checks=all(all(c.values()) for c in checks.values()))
        report.update(outcome='PASS' if all(common.values()) else 'FAIL',checks=common,target_checks=checks,trajectory=trajectory,
            contacts=list(contacts.values()),native_steps=len(measured),native_dt=measured,initialization_callback_count=init,initialization_dt=dts[:init],
            initialization_contacts=initial_contacts,frozen_body_count=frozen,session_disabled_joints=joints,callback_errors=callback_errors,physx_errors=physx_errors,
            manifest_sha256=cfg['manifest_sha256'],scene_sha256=cfg['scene_sha256'],target_state_digest=cfg['state_digest'],
            worker_sha256=sha256_file(__file__),runtime_version=(Path(os.environ['ISAAC_PATH'])/'VERSION').read_text().strip(),source_saved=False)
        report['preserved_instance_colliders']=preserved_instance_colliders
        report['physical_properties']=physical_properties
        omni.timeline.get_timeline_interface().pause()
    except BaseException:
        report.update(outcome='UNKNOWN',exception=traceback.format_exc());traceback.print_exc()
    finally:
        write_json_new(out/'result.json',report)
        if app is not None:app.close(wait_for_replicator=False,exit_code=0 if report['outcome']=='PASS' else 1)


if __name__=='__main__':main()
