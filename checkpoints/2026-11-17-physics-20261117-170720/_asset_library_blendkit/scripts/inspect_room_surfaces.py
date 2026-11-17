"""Read-only source geometry inventory for independent support expansion."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha
import usd_sdk
usd_sdk.load()
from pxr import Usd,UsdGeom,UsdPhysics

def main():
    config=ROOT/'config/local_pool_batch004_catalog42'
    profile=read(config/'profile.json');deployment=read(config/'deployment.json')
    source=Path(deployment['bindings'][profile['source']['mount']])/profile['source']['path']
    assert sha(source)==profile['source']['sha256']
    stage=Usd.Stage.Open(str(source));cache=UsdGeom.BBoxCache(0,['default','render','proxy']);rows=[]
    for p in stage.Traverse():
        name=str(p.GetPath())
        if not p.IsA(UsdGeom.Mesh) or not any(t in name.lower() for t in ['bed','pillow','cushion','seat','chair','floor','duvet','sheet','mattress']):continue
        bounds=cache.ComputeWorldBound(p).ComputeAlignedRange();lo=list(bounds.GetMin());hi=list(bounds.GetMax())
        mesh=UsdGeom.Mesh(p)
        row=dict(prim=name,bounds=[lo,hi],collision=p.HasAPI(UsdPhysics.CollisionAPI),subdivision=mesh.GetSubdivisionSchemeAttr().Get(),vertices=len(mesh.GetPointsAttr().Get() or []))
        rows.append(row);print(row,flush=True)
    write(ROOT/'reports/expanded_support_source_inventory.json',dict(source=str(source),sha256=sha(source),meshes=rows,
        existing_supports=[dict(support_id=s['support_id'],collider=s['collider'],region=s['allowed_region']) for s in profile['supports']]))

if __name__=='__main__':main()
