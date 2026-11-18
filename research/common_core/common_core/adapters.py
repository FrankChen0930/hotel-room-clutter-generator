"""Mesh-top extraction adapted from pinned Hotel helper; primitive math from Toolkit.

Changes: no historical imports, no room names, explicit unsupported results,
and conservative convex coverage proof before certifying a mesh support.
"""
import math

EPS=1e-8


def cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def area(poly):
    return abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1]
                   for i in range(len(poly))))/2 if len(poly)>=3 else 0.


def convex_hull(points):
    points=sorted(set(tuple(p) for p in points))
    if len(points)<3:return []
    def half(seq):
        out=[]
        for p in seq:
            while len(out)>=2 and cross(out[-2],out[-1],p)<=EPS:out.pop()
            out.append(p)
        return out
    return half(points)[:-1]+half(points[::-1])[:-1]


def intersection(subject, clip):
    """Clip a convex polygon against another CCW convex polygon."""
    out=list(subject)
    for i,a in enumerate(clip):
        b=clip[(i+1)%len(clip)];old=out;out=[]
        if not old:break
        for j,p in enumerate(old):
            q=old[(j+1)%len(old)];dp=cross(a,b,p);dq=cross(a,b,q)
            if dp>=-EPS:out.append(p)
            if (dp>EPS and dq<-EPS) or (dp<-EPS and dq>EPS):
                t=dp/(dp-dq);out.append([p[k]+t*(q[k]-p[k]) for k in range(2)])
    return out


def unknown(reason,path=''):
    return dict(status='UNKNOWN',reason=reason,prim=path)


def extract_support(stage, prim):
    from pxr import Gf,UsdGeom
    if not prim:return unknown('MISSING_PRIM')
    path=str(prim.GetPath())
    if UsdGeom.GetStageMetersPerUnit(stage)!=1 or UsdGeom.GetStageUpAxis(stage)!='Z':
        return unknown('UNSUPPORTED_COORDINATES',path)
    if not prim.IsA(UsdGeom.Xformable):return unknown('NO_TRANSFORM',path)
    world=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
    rows=[[float(world[i][j]) for j in range(3)] for i in range(3)]
    if not all(math.isfinite(float(world[i][j])) for i in range(4) for j in range(4)):
        return unknown('NONFINITE_TRANSFORM',path)
    scale=[math.sqrt(sum(x*x for x in r)) for r in rows]
    if min(scale)<EPS:return unknown('SINGULAR_TRANSFORM',path)
    axes=[[x/s for x in r] for r,s in zip(rows,scale)]
    dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    orthogonal=all(abs(dot(axes[i],axes[j]))<EPS for i in range(3) for j in range(i))
    center=list(world.ExtractTranslation())
    base=dict(status='SUPPORTED',prim=path,world_matrix=[[float(world[i][j]) for j in range(4)] for i in range(4)],
              scope='geometric planar coverage only; no native support or physics claim')
    if prim.IsA(UsdGeom.Cube):
        if not orthogonal or abs(abs(axes[2][2])-1)>EPS:return unknown('TILTED_OR_SHEARED_CUBE',path)
        size=float(UsdGeom.Cube(prim).GetSizeAttr().Get())
        if size<=0:return unknown('INVALID_DIMENSION',path)
        xy=[[center[k]+size/2*(a*rows[0][k]+b*rows[1][k]) for k in range(2)] for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        return dict(base,shape='polygon',polygon=convex_hull(xy),z=center[2]+size/2*scale[2])
    if prim.IsA(UsdGeom.Cylinder):
        c=UsdGeom.Cylinder(prim);axis=('X','Y','Z').index(c.GetAxisAttr().Get());radial=[i for i in range(3) if i!=axis]
        if not orthogonal or abs(abs(axes[axis][2])-1)>EPS or abs(scale[radial[0]]-scale[radial[1]])>EPS:
            return unknown('TILTED_SHEARED_OR_ELLIPTICAL_CYLINDER',path)
        r=float(c.GetRadiusAttr().Get());h=float(c.GetHeightAttr().Get())
        if r<=0 or h<=0:return unknown('INVALID_DIMENSION',path)
        return dict(base,shape='circle',center=center[:2],radius=r*scale[radial[0]],z=center[2]+h/2*scale[axis])
    if prim.IsA(UsdGeom.Mesh):
        mesh=UsdGeom.Mesh(prim)
        if mesh.GetSubdivisionSchemeAttr().Get() not in ('none',None):
            return unknown('SUBDIVIDED_SURFACE_NOT_PROVEN',path)
        points=mesh.GetPointsAttr().Get();counts=mesh.GetFaceVertexCountsAttr().Get();ids=mesh.GetFaceVertexIndicesAttr().Get()
        if points is None or counts is None or ids is None:return unknown('MISSING_MESH_TOPOLOGY',path)
        pts=[list(world.Transform(Gf.Vec3d(p))) for p in points]
        top=[];offset=0;holes=set(mesh.GetHoleIndicesAttr().Get() or [])
        for face,n in enumerate(counts):
            face_ids=ids[offset:offset+n];offset+=n
            if face in holes:continue
            if any(i<0 or i>=len(pts) for i in face_ids):return unknown('INVALID_MESH_INDICES',path)
            vertices=[pts[i] for i in face_ids]
            if n<3:continue
            if max(p[2] for p in vertices)-min(p[2] for p in vertices)>1e-6:continue
            polygon=convex_hull([p[:2] for p in vertices])
            if abs(area(polygon)-area([p[:2] for p in vertices]))>EPS:
                return unknown('NONCONVEX_FACE',path)
            if area(polygon)>EPS:top.append((sum(p[2] for p in vertices)/n,polygon))
        if not top:return unknown('NO_PLANAR_TOP',path)
        z=max(t[0] for t in top);polygons=[p for h,p in top if abs(h-z)<1e-6]
        # Bound this proof; a complex top can be replaced by an explicit profile region later.
        if len(polygons)>2000:return unknown('MESH_TOP_PROOF_BUDGET',path)
        hull=convex_hull([p for poly in polygons for p in poly]);total=sum(area(p) for p in polygons)
        if abs(total-area(hull))>max(EPS,area(hull)*1e-6):return unknown('CONCAVE_OR_HOLED_TOP',path)
        for i,p in enumerate(polygons):
            for q in polygons[:i]:
                if area(intersection(p,q))>EPS:return unknown('OVERLAPPING_TOP_FACES',path)
        return dict(base,shape='polygon',polygon=hull,z=z,proof='nonoverlapping convex faces exactly cover convex hull')
    return unknown('UNSUPPORTED_GEOMETRY_TYPE: '+prim.GetTypeName(),path)


def footprint_supported(support, polygon, margin):
    if support['status']!='SUPPORTED' or len(polygon)<3 or margin<0:return False
    if support['shape']=='circle':
        c=support['center'];r=support['radius']-margin
        return r>=0 and all(math.hypot(p[0]-c[0],p[1]-c[1])<=r+EPS for p in polygon)
    region=support['polygon']
    return all(cross(a,region[(i+1)%len(region)],p)>=margin*math.dist(a,region[(i+1)%len(region)])-EPS
               for i,a in enumerate(region) for p in polygon)
