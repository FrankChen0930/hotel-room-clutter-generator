"""Read-only offline USD integrity/static inspection using installed Isaac bindings."""
import argparse
import math
from pathlib import Path
import usd_sdk
from library import sha, write

def inspect(path, self_contained=True):
    Usd=usd_sdk.load()
    from pxr import UsdGeom, UsdShade, UsdUtils, Sdf
    p=Path(path).resolve(strict=True); stage=Usd.Stage.Open(str(p)); errors=[]
    if not stage: raise ValueError('STAGE_OPEN_FAILED')
    layers,assets,unresolved=UsdUtils.ComputeAllDependencies(Sdf.AssetPath(str(p)))
    dependencies=sorted({str(Path(x.realPath).resolve()) for x in layers if x.realPath}|{str(Path(str(x)).resolve()) for x in assets})
    external=[x for x in dependencies if not Path(x).is_relative_to(p.parent)]
    if unresolved: errors.append('UNRESOLVED_DEPENDENCIES')
    if self_contained and external: errors.append('EXTERNAL_DEPENDENCIES')
    if UsdGeom.GetStageUpAxis(stage)!='Z': errors.append('NOT_Z_UP')
    if abs(UsdGeom.GetStageMetersPerUnit(stage)-1)>1e-8: errors.append('NOT_METERS')
    root=stage.GetDefaultPrim()
    if not root: errors.append('DEFAULT_PRIM_MISSING')
    meshes=[UsdGeom.Mesh(x) for x in stage.Traverse() if x.IsA(UsdGeom.Mesh)]
    if not meshes: errors.append('NO_MESH')
    unbound=[]; uv=[]
    for prim in stage.Traverse():
        if prim.IsA(UsdShade.Shader) and UsdShade.Shader(prim).GetIdAttr().Get()=='UsdUVTexture':
            value=UsdShade.Shader(prim).GetInput('file').Get()
            if value and Path(value.path).suffix.lower() not in {'.png','.jpg','.jpeg','.tif','.tiff','.exr','.hdr','.dds','.bmp','.tga','.webp'}:
                errors.append('UNSUPPORTED_TEXTURE_EXTENSION:'+str(prim.GetPath()))
    for m in meshes:
        points=m.GetPointsAttr().Get() or []
        if not points or any(not math.isfinite(float(v)) for pt in points for v in pt): errors.append('INVALID_POINTS:'+str(m.GetPath()))
        mat,_=UsdShade.MaterialBindingAPI(m.GetPrim()).ComputeBoundMaterial()
        subsets=UsdShade.MaterialBindingAPI(m.GetPrim()).GetMaterialBindSubsets()
        if not mat and not subsets: unbound.append(str(m.GetPath()))
        if not mat and subsets:
            covered=set()
            for sub in subsets:
                submat,_=UsdShade.MaterialBindingAPI(sub.GetPrim()).ComputeBoundMaterial()
                if submat: covered.update(sub.GetIndicesAttr().Get() or [])
            if covered!=set(range(len(m.GetFaceVertexCountsAttr().Get() or []))):
                unbound.append(str(m.GetPath())+':incomplete_subset_coverage')
        uv.append(dict(mesh=str(m.GetPath()),primvars=[x.GetPrimvarName() for x in UsdGeom.PrimvarsAPI(m).GetPrimvars()]))
    if unbound: errors.append('UNBOUND_MESHES')
    bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy']).ComputeWorldBound(root).ComputeAlignedRange() if root else None
    lo=list(bbox.GetMin()) if bbox else None; hi=list(bbox.GetMax()) if bbox else None
    dims=[hi[i]-lo[i] for i in range(3)] if bbox else None
    if dims and (any(not math.isfinite(x) or x<=0 for x in dims)): errors.append('INVALID_DIMENSIONS')
    if lo and (abs(lo[2])>.001 or abs((lo[0]+hi[0])/2)>.001 or abs((lo[1]+hi[1])/2)>.001): errors.append('PIVOT_NOT_BOTTOM_CENTER')
    return dict(outcome='PASS' if not errors else 'FAIL',usd_sha256=sha(p),errors=errors,
        mesh_count=len(meshes),unbound_meshes=unbound,uv=uv,dimensions_m=dims,bounds_m=[lo,hi],
        root_prim=str(root.GetPath()) if root else None,unresolved=list(map(str,unresolved)),external_dependencies=external,
        dependencies=[dict(path=x,sha256=sha(x)) for x in dependencies if Path(x).is_file()],
        scope='Offline integrity and origin checks only; no visual, native support, collision or dynamic qualification')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--usd',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    if a.output.exists(): raise ValueError('NEW_REPORT_PATH_REQUIRED')
    r=inspect(a.usd); write(a.output,r); print(r['outcome'],r['errors']); raise SystemExit(r['outcome']!='PASS')
