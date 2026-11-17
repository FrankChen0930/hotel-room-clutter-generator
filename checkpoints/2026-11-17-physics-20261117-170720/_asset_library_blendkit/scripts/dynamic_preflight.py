"""Session-only rigid surrogate preparation. Never modifies source asset layers."""
def disable_empty_colliders(stage):
    from pxr import UsdGeom,UsdPhysics
    disabled=[]
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh) and prim.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()!=False:
            if not UsdGeom.Mesh(prim).GetPointsAttr().Get():
                UsdPhysics.CollisionAPI(prim).CreateCollisionEnabledAttr(False);disabled.append(str(prim.GetPath()))
    return disabled

def prepare_generated(stage, generated, native_tuning=True):
    from pxr import Usd,UsdGeom,UsdPhysics,UsdShade,Gf
    if native_tuning:from pxr import PhysxSchema
    cache=UsdGeom.BBoxCache(0,['default','render','proxy']);rows=[]
    material=UsdShade.Material.Define(stage,'/ExperimentalPhysics/Materials/DryRigid')
    physical=UsdPhysics.MaterialAPI.Apply(material.GetPrim());physical.CreateStaticFrictionAttr(.6);physical.CreateDynamicFrictionAttr(.5);physical.CreateRestitutionAttr(0.)
    for path,meta in generated.items():
        root=stage.GetPrimAtPath(path)
        assert root and root.HasAPI(UsdPhysics.RigidBodyAPI),path
        descendants=list(Usd.PrimRange(root));disabled=[];colliders=[]
        for p in descendants:
            if p!=root and p.HasAPI(UsdPhysics.RigidBodyAPI):
                p.RemoveAPI(UsdPhysics.RigidBodyAPI);disabled.append(str(p.GetPath()))
            if p.IsA(UsdPhysics.Joint):UsdPhysics.Joint(p).CreateJointEnabledAttr(False)
            if p.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()!=False:
                colliders.append(p)
        fallback=False
        if not colliders:
            # Existing thin research paper/wrapper had no collider at all. Explicit rigid
            # envelope, not a flexible-paper claim. Preserve actual bottom and footprint.
            r=cache.ComputeUntransformedBound(root).ComputeAlignedRange();lo=r.GetMin();hi=r.GetMax();d=hi-lo
            assert all(v>0 for v in d),path
            d=Gf.Vec3d(d[0],d[1],max(d[2],.001))
            cube=UsdGeom.Cube.Define(stage,path+'/ExperimentalRigidEnvelope');cube.CreateSizeAttr(1);cube.CreateVisibilityAttr('invisible')
            matrix=Gf.Matrix4d(1).SetScale(d);matrix.SetTranslateOnly(Gf.Vec3d((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]+d[2]/2))
            UsdGeom.Xformable(cube).AddTransformOp().Set(matrix);UsdPhysics.CollisionAPI.Apply(cube.GetPrim());colliders=[cube.GetPrim()];fallback=True
        if native_tuning:
            for p in colliders:
                UsdShade.MaterialBindingAPI.Apply(p).Bind(material,materialPurpose='physics')
                api=PhysxSchema.PhysxCollisionAPI.Apply(p);api.CreateContactOffsetAttr(.002);api.CreateRestOffsetAttr(0.)
            body=PhysxSchema.PhysxRigidBodyAPI.Apply(root);body.CreateEnableCCDAttr(True);body.CreateSolverPositionIterationCountAttr(32);body.CreateSolverVelocityIterationCountAttr(8)
        rows.append(dict(prim=path,nested_body_apis_removed=disabled,colliders=[str(p.GetPath()) for p in colliders],rigid_envelope_added=fallback))
    return dict(outcome='PASS',generated_root_count=len(rows),bodies=rows,scope='Experimental rigid surrogates; no soft-body or calibrated manipulation qualification')
