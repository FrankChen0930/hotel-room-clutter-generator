"""Independent measured support adapter; original furniture and formal Core stay read-only."""
from pathlib import Path
import math
from library import ROOT,read,write,sha
import usd_sdk
usd_sdk.load()
from pxr import Usd,UsdGeom,Gf
from surface_geometry import read_mesh,rectangle,fit_horizontal,footprint_grid,np

CURVED={
 'bed_main':('/root/_7052_Asset_double_duvet/_7052_Double_Duvet_Turnback/_7052_thick_folded_duvet_volume',[.62,-5.73],[1.78,-4.27]),
 'bed_single':('/root/_7052_Asset_sofa_seat_cushion/_7052_Sofa_Seat_Upholstery/__________525',[.66,-3.43],[1.48,-2.96]),
 'pillow_left':('/root/Pillow_Left/Pillow_Left_envelope',[1.97,-4.82],[2.39,-4.24]),
 'pillow_right':('/root/Pillow_Right/Pillow_Right_envelope',[1.97,-5.72],[2.39,-5.14]),
 'chair_seat':('/root/_7052_Armchair_Seat_Pad/_7052_Armchair_Seat_Pad_001',[-.69,-7.49],[-.31,-7.23]),
}

class Surfaces:
    def __init__(self,profile,bindings):
        self.source=Path(bindings[profile['source']['mount']])/profile['source']['path']
        assert sha(self.source)==profile['source']['sha256']
        self.stage=Usd.Stage.Open(str(self.source));self.meshes={};self.specs={};self.obstacle_meshes={}
        from common_core.room import geometry_signature
        from common_core.adapters import extract_support
        for spec in profile['supports']:
            sid=spec['support_id'];prim=self.stage.GetPrimAtPath(spec['collider'])
            if prim.IsA(UsdGeom.Mesh):
                self.meshes[sid]=self.mesh_for(prim)
                self.specs[sid]=dict(support_id=sid,collider=spec['collider'],region=spec['allowed_region'],kind='measured_source_mesh',relief_limit_m=.008,geometry_hash=geometry_signature(prim))
        floor='/root/_7052_Floor_Backfill/Cube_002'
        extras={**CURVED,'floor_between_beds':(floor,[.65,-4.04],[1.55,-3.70]),
            'floor_window_side':(floor,[1.72,-7.55],[2.38,-6.35])}
        for sid,(path,lo,hi) in extras.items():
            prim=self.stage.GetPrimAtPath(path)
            if not prim:raise ValueError('SOURCE_SUPPORT_MISSING:'+path)
            self.meshes[sid]=self.mesh_for(prim)
            self.specs[sid]=dict(support_id=sid,collider=path,region=rectangle(lo,hi),kind='measured_source_triangle_surface',relief_limit_m=.008,
                geometry_hash=geometry_signature(prim),soft_surface=sid.startswith(('bed_','pillow_')) or sid=='chair_seat')
        bbox=UsdGeom.BBoxCache(0,['default','render','proxy']);self.obstacles=[]
        for p in self.stage.Traverse():
            if not p.IsA(UsdGeom.Mesh):continue
            if UsdGeom.Imageable(p).ComputeVisibility()=='invisible':continue
            b=bbox.ComputeWorldBound(p).ComputeAlignedRange();lo=list(b.GetMin());hi=list(b.GetMax())
            self.obstacles.append((p,lo,hi))

    def mesh_for(self,prim):
        path=str(prim.GetPath())
        if path not in self.obstacle_meshes:self.obstacle_meshes[path]=read_mesh(prim)
        return self.obstacle_meshes[path]

    def source_collision(self,box,support_id):
        lo,hi=np.asarray(box[0]),np.asarray(box[1]);expected=self.specs[support_id]['collider']
        # Triangle AABBs conservatively over-reject near curved furniture edges.
        # The supporting source mesh itself is separately checked with dense rays.
        for prim,a,b in self.obstacles:
            if str(prim.GetPath())==expected:continue
            if not all(a[i]<hi[i]-.0001 and b[i]>lo[i]+.0001 for i in range(3)):continue
            mesh=self.mesh_for(prim);tri=mesh.xyz
            hit=np.all(tri.min(axis=1)<hi-.0001,axis=1)&np.all(tri.max(axis=1)>lo+.0001,axis=1)
            if np.any(hit):return str(prim.GetPath())
        return None

    def fit(self,sid,bounds,x,y,yaw,n=9,exact=False):
        if exact and sid in CURVED:
            n=max(9,math.ceil(max(bounds[1][i]-bounds[0][i] for i in range(2))/.012)+1)
        fit=fit_horizontal(self.meshes[sid],footprint_grid(bounds,x,y,yaw,n),self.specs[sid]['relief_limit_m'])
        if fit is None or not exact:return fit
        c=math.cos(yaw);s=math.sin(yaw)
        footprint=[[x+c*u-s*v,y+s*u+c*v] for u,v in [(bounds[0][0],bounds[0][1]),(bounds[1][0],bounds[0][1]),(bounds[1][0],bounds[1][1]),(bounds[0][0],bounds[1][1])]]
        peak=self.meshes[sid].peak_over_polygon(footprint)
        if peak is None or peak-fit['min_z']>self.specs[sid]['relief_limit_m']:return None
        fit.update(z=peak,relief_m=peak-fit['min_z'],max_clearance_m=peak-fit['min_z']+.001,exact_triangle_peak=True,
            scope='Exact maximum of unchanged source triangles clipped to footprint plus dense upper-envelope gap samples; no deformation/dynamics')
        return fit

    def record(self):
        return dict(source=str(self.source),source_sha256=sha(self.source),surfaces=list(self.specs.values()),
            contact_scope='Exact clipped triangle maximum;81+ source height queries and <=12mm grid spacing on curved supports; <=8mm sampled relief plus1mm clearance; source furniture fixed',
            native_scope='Exact unchanged source mesh triangle collider in unsaved static session; original collider approximation separately disclosed',
            adapter_sha256=sha(__file__),geometry_helper_sha256=sha(ROOT/'scripts/surface_geometry.py'))
