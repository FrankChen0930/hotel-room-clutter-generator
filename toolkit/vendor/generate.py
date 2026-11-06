import sys,math,random,itertools
from datetime import datetime,timezone
from pathlib import Path
from common import *
import geometry_check as geometry
CONFIG=read(CONFIG_DIR/'prototype_config.json')
FLOOR=PREFIX+'/ShellColliders/Floor'
_helper_stage=Usd.Stage.CreateInMemory()
_cube=U.Cube.Define(_helper_stage,'/Box');_cube.CreateSizeAttr(1)

def box_shape(box, delta=Gf.Matrix4d(1)):
    lo, hi = box['min'], box['max']
    m = Gf.Matrix4d(1).SetScale(Gf.Vec3d(*[hi[i]-lo[i] for i in range(3)]))
    m.SetTranslateOnly(Gf.Vec3d(*[(hi[i]+lo[i])/2 for i in range(3)]))
    return geometry.extract_primitive(_helper_stage, _cube.GetPrim(), m*delta)

def corners(shape):
    c, a, h = shape['center_xy'], shape['axes_xy'], shape['half_sizes_xy_m']
    return [[c[i]+u*h[0]*a[0][i]+v*h[1]*a[1][i] for i in range(2)] for u,v in [(-1,-1),(1,-1),(1,1),(-1,1)]]

def pair(a,b,margin=.01):
    # Reuse Phase2 circle/OBB primitive checks; Phase3-style upright rectangle SAT.
    if a['kind']=='circle': return geometry.pair_check(a,b,margin)['status']
    if b['kind']=='circle': return geometry.pair_check(b,a,margin)['status']
    if geometry.aabb_gap(a['world_aabb'],b['world_aabb']) > margin+geometry.EPS: return 'PASS'
    if a['kind']!='rectangle' or b['kind']!='rectangle': return 'UNKNOWN'
    gaps = [max(a['z_min']-b['z_max'],b['z_min']-a['z_max'])]
    for axis in a['axes_xy']+b['axes_xy']:
        pa=[geometry.dot(p,axis) for p in corners(a)]; pb=[geometry.dot(p,axis) for p in corners(b)]
        gaps.append(max(min(pa)-max(pb),min(pb)-max(pa)))
    return 'PASS' if max(gaps)>margin+geometry.EPS else 'REJECT'

def contains(support, shape, margin=.01):
    points = corners(shape)
    if support['kind']=='circle':
        return min(support['radius_m']-math.dist(p,support['center_xy']) for p in points) >= margin
    if support['kind']!='rectangle': return False
    return min(h-abs(geometry.dot([p[i]-support['center_xy'][i] for i in range(2)],axis))
               for p in points for h,axis in zip(support['half_sizes_xy_m'],support['axes_xy'])) >= margin

def discover(source):
    allp = prims(source); cache=U.XformCache()
    colliders = {str(p.GetPath()):geometry.extract_primitive(source,p) for p in allp
                 if p.HasAPI(P.CollisionAPI) and P.CollisionAPI(p).GetCollisionEnabledAttr().Get()}
    groups={}
    for key,cfg in CONFIG['groups'].items():
        if 'root' in cfg:
            roots=[cfg['root']]
            cp=[p for p in colliders if p.startswith(cfg['root']+'/')]
        else:
            roots=[str(p.GetPath()) for p in source.GetPrimAtPath(PREFIX+'/Shell').GetChildren() if p.GetName().startswith(cfg['shell_prefix'])]
            cp=[p for p in colliders if p.split('/')[-1].startswith(cfg['shell_prefix']) and p.startswith(PREFIX+'/ShellColliders/')]
            roots += cp
        visual=[p for p in roots if '/ShellColliders/' not in p]
        assert roots and cp
        groups[key]={'roots':roots,'visual_roots':visual,'colliders':cp,'pivot':cfg['pivot'],
                     'visual_envelope':bounds(source,visual),
                     'original_world':{p:rows(cache.GetLocalToWorldTransform(source.GetPrimAtPath(p))) for p in roots}}
    targets={t for p in allp if p.IsA(P.Joint) for n in ('physics:body0','physics:body1') for t in map(str,p.GetRelationship(n).GetTargets())}
    assert not any(any(t==r or t.startswith(r+'/') for t in targets) for g in groups.values() for r in g['roots'])
    return groups,colliders

def material(s,path,color,rough=.7):
    m=UsdShade.Material.Define(s,path); sh=UsdShade.Shader.Define(s,path+'/Preview')
    sh.CreateIdAttr('UsdPreviewSurface');sh.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    sh.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough)
    m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(),'surface');return m

def rigid_shapes(stage, groups, furniture, colliders):
    bypath={}
    for p,shape in colliders.items():
        owner=next((k for k,g in groups.items() if p in g['colliders']),None)
        if owner:
            m=mat(shape['world_transform'])*mat(furniture[owner]['delta'])
            shape=geometry.extract_primitive(stage,stage.GetPrimAtPath(p),m)
        bypath[p]=shape
    return bypath

def cameras(s):
    for name,pos,target,scale in [('Overview',(8,-6,13),(1.8,4.4,0),10.0),('BedsAndSeating',(7,9,10),(1.8,5.8,.2),6.3)]:
        camera=U.Camera.Define(s,PREFIX+'/V2Cameras/'+name)
        camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(Gf.Vec3d(*pos),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
        camera.CreateProjectionAttr('orthographic');camera.CreateHorizontalApertureAttr(scale*10);camera.CreateVerticalApertureAttr(scale*7.5)
        camera.CreateClippingRangeAttr(Gf.Vec2f(.01,100))

def derive(path, groups, manifest=None):
    assert not path.exists()
    s = Usd.Stage.CreateNew(str(path))
    root = U.Xform.Define(s, PREFIX)
    s.SetDefaultPrim(root.GetPrim())
    root.GetPrim().GetReferences().AddReference(relative(ROOM, path))
    U.SetStageUpAxis(s, 'Z')
    U.SetStageMetersPerUnit(s, 1)
    s.GetRootLayer().customLayerData = {'scope': 'ROOM_CLUTTER_V2_STATIC_PREVIEW', 'physics': 'NOT_RUN', 'fully_validated': False}
    cameras(s)
    if manifest is not None:
        raise RuntimeError('Only wrapper rigid overlay is supported')
    s.GetRootLayer().Save()
    return s
