from library import ROOT,read
import usd_sdk
usd_sdk.load()
from pxr import Usd,UsdGeom,UsdPhysics
import sys
sys.path.insert(0,str(ROOT.parent/'common_core'))
from common_core.writer import object_prim
run=ROOT/'runs/density_dynamics_repair_a001';stage=Usd.Stage.Open(str(run/'runtime_initial.usda'))
objects={object_prim(o):o for o in read(ROOT/'runs/density_v1_a004/high706/manifest.json')['objects']}
for issue in read(run/'result.json')['issues']:
    path=issue['prim'];o=objects[path];print(path,o['asset_id'],o['effective']['support_id'])
    for p in Usd.PrimRange(stage.GetPrimAtPath(path)):
        if p.HasAPI(UsdPhysics.CollisionAPI):print(' collider',str(p.GetPath()),p.GetTypeName(),'enabled',UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get(),'approx',UsdPhysics.MeshCollisionAPI(p).GetApproximationAttr().Get() if p.IsA(UsdGeom.Mesh) else '')
