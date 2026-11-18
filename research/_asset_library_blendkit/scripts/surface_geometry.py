"""Measured unchanged triangle surfaces. No hidden support planes or scene edits."""
import math
try:
    import numpy as np
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    bundles=list(Path('C:/isaac_sim/extscache').glob('omni.kit.pip_archive-*/pip_prebundle'))
    if len(bundles)!=1:raise RuntimeError('AMBIGUOUS_INSTALLED_NUMPY')
    sys.path.insert(0,str(bundles[0]))
    import numpy as np

class HeightMesh:
    def __init__(self,points,triangles,cell=.08):
        self.points=np.asarray(points,dtype=float);self.triangles=np.asarray(triangles,dtype=int)
        self.xyz=self.points[self.triangles];self.cell=cell;self.grid={}
        xy=self.xyz[:,:,:2];self.lo=xy.min(axis=1);self.hi=xy.max(axis=1)
        a=xy[:,1]-xy[:,0];b=xy[:,2]-xy[:,0]
        self.det=a[:,0]*b[:,1]-a[:,1]*b[:,0]
        for i in np.where(np.abs(self.det)>1e-12)[0]:
            lo=np.floor(self.lo[i]/cell).astype(int);hi=np.floor(self.hi[i]/cell).astype(int)
            for x in range(lo[0],hi[0]+1):
                for y in range(lo[1],hi[1]+1):self.grid.setdefault((x,y),[]).append(int(i))
        self.grid={k:np.asarray(v,dtype=int) for k,v in self.grid.items()}

    def height(self,x,y):
        ids=self.grid.get((math.floor(x/self.cell),math.floor(y/self.cell)))
        if ids is None:return None
        q=self.xyz[ids];a=q[:,1,:2]-q[:,0,:2];b=q[:,2,:2]-q[:,0,:2];d=np.array([x,y])-q[:,0,:2]
        u=(d[:,0]*b[:,1]-d[:,1]*b[:,0])/self.det[ids]
        v=(a[:,0]*d[:,1]-a[:,1]*d[:,0])/self.det[ids]
        inside=(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)
        if not np.any(inside):return None
        h=q[:,0,2]+u*(q[:,1,2]-q[:,0,2])+v*(q[:,2,2]-q[:,0,2])
        return float(h[inside].max())

    def peak_over_polygon(self,polygon):
        """Exact maximum of source triangles clipped to a convex footprint."""
        lo=np.min(polygon,axis=0);hi=np.max(polygon,axis=0)
        ids=np.where((self.hi[:,0]>=lo[0])&(self.lo[:,0]<=hi[0])&(self.hi[:,1]>=lo[1])&(self.lo[:,1]<=hi[1])&(np.abs(self.det)>1e-12))[0]
        highest=None
        for index in ids:
            output=self.xyz[index].tolist()
            for k,a in enumerate(polygon):
                b=polygon[(k+1)%len(polygon)];old=output;output=[]
                if not old:break
                def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
                for j,p in enumerate(old):
                    q=old[(j+1)%len(old)];dp=side(p);dq=side(q)
                    if dp>=-1e-10:output.append(p)
                    if (dp>0 and dq<0) or (dp<0 and dq>0):
                        t=dp/(dp-dq);output.append([p[v]+t*(q[v]-p[v]) for v in range(3)])
            if output:
                peak=max(p[2] for p in output);highest=peak if highest is None else max(highest,peak)
        return highest

def read_mesh(prim):
    from pxr import UsdGeom,Gf
    mesh=UsdGeom.Mesh(prim);matrix=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
    points=[list(matrix.Transform(Gf.Vec3d(v))) for v in mesh.GetPointsAttr().Get()]
    ids=list(mesh.GetFaceVertexIndicesAttr().Get());triangles=[];offset=0
    holes=set(mesh.GetHoleIndicesAttr().Get() or [])
    for face,n in enumerate(mesh.GetFaceVertexCountsAttr().Get()):
        f=ids[offset:offset+n];offset+=n
        if face not in holes:triangles.extend((f[0],f[i],f[i+1]) for i in range(1,n-1))
    return HeightMesh(points,triangles)

def rectangle(lo,hi):return [[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]]

def footprint_grid(bounds,x,y,yaw,n=9):
    c=math.cos(yaw);s=math.sin(yaw)
    return [[x+c*u-s*v,y+s*u+c*v] for u in np.linspace(bounds[0][0],bounds[1][0],n) for v in np.linspace(bounds[0][1],bounds[1][1],n)]

def fit_horizontal(mesh,points,max_relief=.008):
    heights=[mesh.height(*p) for p in points]
    if any(h is None for h in heights):return None
    relief=max(heights)-min(heights)
    if relief>max_relief:return None
    return dict(z=max(heights),min_z=min(heights),relief_m=relief,points=points,heights=heights,
        clearance_m=.001,max_clearance_m=relief+.001,scope='Finite dense triangle-height samples over conservative asset footprint; no deformation or dynamic stability')
