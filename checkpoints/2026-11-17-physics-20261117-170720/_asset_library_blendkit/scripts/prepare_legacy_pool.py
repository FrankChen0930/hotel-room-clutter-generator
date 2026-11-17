"""Reuse existing room props, explicitly outside Blendkit asset-library counts."""
from library import ROOT,read,write,sha
import usd_sdk
usd_sdk.load()
from pxr import Usd,UsdGeom,UsdPhysics,Sdf,Gf

def main():
    source=read(ROOT/'reports/room_authored_physics_inventory.json')['source'];stage=Usd.Stage.Open(source);flat=stage.Flatten()
    folder=ROOT/'artifacts/legacy_density_pool_a001';folder.mkdir(exist_ok=False)
    entries=[]
    for key in ['native_water1','native_water2','native_mug1','native_tea1','native_cookiepack1']:
        cat={'native_water1':'water','native_water2':'water','native_mug1':'mug','native_tea1':'tea','native_cookiepack1':'snack'}[key]
        path={'native_water1':'/root/Water1','native_water2':'/root/Water2','native_mug1':'/root/Mug1','native_tea1':'/root/Tea1','native_cookiepack1':'/root/CookiePack1'}[key]
        dest=folder/(key+'.usda');s=Usd.Stage.CreateNew(str(dest));root=UsdGeom.Xform.Define(s,'/Asset');s.SetDefaultPrim(root.GetPrim());UsdGeom.SetStageUpAxis(s,'Z');UsdGeom.SetStageMetersPerUnit(s,1)
        Sdf.CopySpec(flat,path,s.GetRootLayer(),'/Asset/Visual')
        Sdf.CopySpec(flat,'/root/_materials',s.GetRootLayer(),'/Asset/Materials')
        for prim in s.Traverse():
            for attr in prim.GetAttributes():
                connections=attr.GetConnections()
                if connections:attr.SetConnections([p.ReplacePrefix('/root/_materials','/Asset/Materials') for p in connections])
            for rel in prim.GetRelationships():rel.SetTargets([p.ReplacePrefix('/root/_materials','/Asset/Materials') for p in rel.GetTargets()])
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
        cache=UsdGeom.BBoxCache(0,['default']);r=cache.ComputeWorldBound(root.GetPrim()).ComputeAlignedRange();lo=r.GetMin();hi=r.GetMax();d=hi-lo
        xf=UsdGeom.Xformable(s.GetPrimAtPath('/Asset/Visual'));m=xf.GetLocalTransformation();xf.ClearXformOpOrder();xf.AddTransformOp().Set(m*Gf.Matrix4d().SetTranslate((-lo[0]-d[0]/2,-lo[1]-d[1]/2,-lo[2])))
        for prim in s.Traverse():
            if prim.HasAPI(UsdPhysics.CollisionAPI):UsdPhysics.CollisionAPI(prim).CreateCollisionEnabledAttr(False)
        proxy=UsdGeom.Cube.Define(s,'/Asset/Proxy');proxy.CreateSizeAttr(1);proxy.CreateVisibilityAttr('invisible');p=UsdGeom.Xformable(proxy);p.AddScaleOp().Set(Gf.Vec3f(*d));p.AddTranslateOp().Set(Gf.Vec3d(0,0,d[2]/2))
        # Translate follows scale in USD op order; use a single matrix instead.
        p.ClearXformOpOrder();matrix=Gf.Matrix4d(1);matrix.SetScale(d);matrix.SetTranslateOnly(Gf.Vec3d(0,0,d[2]/2));p.AddTransformOp().Set(matrix)
        UsdPhysics.CollisionAPI.Apply(proxy.GetPrim());s.GetRootLayer().Save()
        entries.append(dict(asset_id='legacy-'+key,category=cat,dimensions_m=list(d),state_id='default',source_kind='EXISTING_ROOM_NOT_NEW_BLENDKIT',usd_path=str(dest)))
    # Existing paper assets need no conversion. Keep their source bytes and old scope.
    original=read(ROOT/'config/local_pool_batch004_catalog42/catalog.json')['entries']
    for key in ['paper_0','paper_1','paper_2','paper_r1','wrapper_r1']:
        e=next(e for e in original if e['asset_id']==key)
        entries.append(dict(asset_id=key,category=e['category'],dimensions_m=e['dimensions'],state_id='default',catalog_entry=e,source_kind='EXISTING_RESEARCH_NOT_NEW_BLENDKIT'))
    write(folder/'index.json',entries)

if __name__=='__main__':main()
