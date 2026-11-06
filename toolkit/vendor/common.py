import os,sys,json,hashlib
from pathlib import Path
from pxr import Usd,UsdGeom as U,UsdPhysics as P,UsdShade,Sdf,Gf,UsdUtils
TOOLKIT=Path(__file__).resolve().parents[1]
HERE=TOOLKIT/'vendor'
ROOT=TOOLKIT.parent.parent/'asset-package/assets'
CONFIG_DIR=TOOLKIT/'config'
ROOM=ROOT/'room/usd/YAZHI_TWIN.usd'
PREFIX='/YAZHI_TWIN'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
rows=lambda m:[[float(m[i][j]) for j in range(4)] for i in range(4)]
mat=lambda a:Gf.Matrix4d(*[v for r in a for v in r])

def prims(s): return list(Usd.PrimRange.Stage(s, Usd.TraverseInstanceProxies()))

def bounds(s, paths):
    cache = U.BBoxCache(Usd.TimeCode.Default(), ['default','render'], False, True)
    box = Gf.Range3d()
    for path in paths: box.UnionWith(cache.ComputeWorldBound(s.GetPrimAtPath(path)).ComputeAlignedRange())
    assert not box.IsEmpty(), paths
    return {'min':list(box.GetMin()), 'max':list(box.GetMax())}

def pose(x,y,z,yaw=0):
    m = Gf.Matrix4d(1).SetRotate(Gf.Rotation(Gf.Vec3d(0,0,1),yaw))
    m.SetTranslateOnly(Gf.Vec3d(x,y,z)); return m

def set_world(s, path, world):
    p = s.GetPrimAtPath(path)
    parent = U.XformCache().GetLocalToWorldTransform(p.GetParent())
    xf = U.Xformable(p); xf.ClearXformOpOrder()
    xf.AddTransformOp(U.XformOp.PrecisionDouble, 'v2Preview').Set(world*parent.GetInverse())

def relative(target, anchor): return os.path.relpath(target, Path(anchor).parent).replace('\\','/')
