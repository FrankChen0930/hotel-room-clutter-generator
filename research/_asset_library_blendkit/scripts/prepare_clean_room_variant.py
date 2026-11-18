"""Retain source geometry/layout and only source-root physics preparation opinions."""
import argparse
from pathlib import Path
import os
from library import ROOT,read,write,sha
import usd_sdk


def main():
    p=argparse.ArgumentParser();p.add_argument('--initial-opinions',type=Path,required=True);p.add_argument('--tag',required=True);a=p.parse_args()
    usd_sdk.load()
    from pxr import Sdf,Usd,UsdGeom,UsdUtils
    source=Path(read(ROOT/'reports/room_authored_physics_inventory.json')['source']);before=sha(source)
    original=Usd.Stage.Open(str(source));names={p.GetName() for p in original.GetPseudoRoot().GetChildren()}
    out=ROOT/'runs'/a.tag;out.mkdir(exist_ok=False)
    layer=Sdf.Layer.CreateAnonymous();layer.TransferContent(Sdf.Layer.FindOrOpen(str(a.initial_opinions)))
    removed=[]
    for spec in list(layer.rootPrims):
        if spec.name not in names:removed.append(spec.name);del layer.rootPrims[spec.name]
    opinions=out/'physics_opinions.usda';assert layer.Export(str(opinions))
    scene=out/'scene.usda';stage=Usd.Stage.CreateNew(str(scene));stage.GetRootLayer().subLayerPaths=['physics_opinions.usda',os.path.relpath(source,out).replace('\\','/')]
    UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1);stage.SetDefaultPrim(stage.GetPrimAtPath('/root'));stage.GetRootLayer().Save()
    assert not stage.GetPrimAtPath('/CommonCore')
    checked=0
    for prim in original.Traverse():
        other=stage.GetPrimAtPath(prim.GetPath());assert other and other.GetTypeName()==prim.GetTypeName()
        if prim.IsA(UsdGeom.Xformable):
            left=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0);right=UsdGeom.Xformable(other).ComputeLocalToWorldTransform(0)
            assert max(abs(left[i][j]-right[i][j]) for i in range(4) for j in range(4))<1e-9
        if prim.IsA(UsdGeom.Mesh):
            for attr in prim.GetAttributes():
                if attr.GetName() in {'points','faceVertexIndices','faceVertexCounts','normals'} or attr.GetName().startswith('primvars:'):
                    assert str(attr.Get())==str(other.GetAttribute(attr.GetName()).Get()),(str(prim.GetPath()),attr.GetName())
            checked+=1
    assert not UsdUtils.ComputeAllDependencies(str(scene))[2] and sha(source)==before
    write(out/'geometry_preservation.json',dict(outcome='PASS',source_sha256=before,scene_sha256=sha(scene),meshes=checked,removed_non_source_opinion_roots=removed,
        scope='Actual source hierarchy, geometry/UV/normals and initial world matrices preserved; source-only physics opinions retained separately. Clean-room native dynamics still pending.'))
    print('CLEAN_ROOM_GEOMETRY_PRESERVED',checked,str(scene))


if __name__=='__main__':main()
