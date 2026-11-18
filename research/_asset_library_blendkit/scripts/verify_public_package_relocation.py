"""Verify a real directory relocation against the exact physics-tested stages."""
import argparse
import hashlib
from pathlib import Path
import shutil
from library import ROOT,read,write,sha
import usd_sdk

def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--relocated',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--clean',type=Path,required=True);a=p.parse_args()
    assert not a.relocated.exists();assert a.relocated.resolve().is_relative_to(ROOT.parent/'_project_delivery')
    receipt=read(a.bundle/'package_manifest.json')
    assert receipt['redistribution']=='HOTEL705_USER_CONFIRMED_AUTHOR_LAB_PERMISSION_ONLY'
    shutil.copytree(a.bundle,a.relocated)
    for row in receipt['files']:assert sha(a.relocated/row['path'])==row['sha256']
    usd_sdk.load()
    from pxr import Usd,UsdGeom,UsdUtils,Sdf
    pairs=[('clean_room.usda',a.clean)]
    for c in read(a.run/'cases.json')['cases']:
        base=f"scenes/{c['level']}_seed_{c['seed']}"
        pairs.extend([(base+'.usda',Path(c['scene'])),(base+'_dynamic.usda',Path(c['dynamic_scene']))])
    digests={}
    def asset_value(v):
        if isinstance(v,Sdf.AssetPath):
            f=Path(v.resolvedPath) if v.resolvedPath else None
            if f and f.is_file():
                key=str(f.resolve());digests.setdefault(key,sha(f));return ('asset-bytes',digests[key])
            return ('unresolved',v.path)
        return v
    checks=[]
    for name,source in pairs:
        target=a.relocated/name
        ls,assets,missing=UsdUtils.ComputeAllDependencies(str(target));assert not missing,(name,missing)
        assert all(Path(x.realPath).resolve().is_relative_to(a.relocated.resolve()) for x in ls)
        assert all(Path(str(x)).resolve().is_relative_to(a.relocated.resolve()) for x in assets)
        orig=Usd.Stage.Open(str(source));moved=Usd.Stage.Open(str(target))
        assert UsdGeom.GetStageUpAxis(orig)==UsdGeom.GetStageUpAxis(moved)=='Z'
        assert UsdGeom.GetStageMetersPerUnit(orig)==UsdGeom.GetStageMetersPerUnit(moved)==1
        assert str(orig.GetDefaultPrim().GetPath())==str(moved.GetDefaultPrim().GetPath())
        original={str(x.GetPath()):x for x in orig.Traverse()};relocated={str(x.GetPath()):x for x in moved.Traverse()}
        assert original.keys()==relocated.keys(),name
        attributes=0;relations=0;meshes=0
        for path,prim in original.items():
            other=relocated[path];assert prim.GetTypeName()==other.GetTypeName(),(name,path)
            left={x.GetName():x for x in prim.GetAttributes()};right={x.GetName():x for x in other.GetAttributes()}
            assert left.keys()==right.keys(),(name,path,'ATTRIBUTES_DIFFER')
            for key,attr in left.items():
                b=right[key];assert attr.GetTypeName()==b.GetTypeName()
                assert asset_value(attr.Get())==asset_value(b.Get()),(name,path,key,'VALUE_CHANGED')
                times=attr.GetTimeSamples();assert times==b.GetTimeSamples()
                for t in times:assert asset_value(attr.Get(t))==asset_value(b.Get(t)),(name,path,key,t)
                attributes+=1
            lrels={r.GetName():list(map(str,r.GetTargets())) for r in prim.GetRelationships()}
            rrels={r.GetName():list(map(str,r.GetTargets())) for r in other.GetRelationships()}
            assert lrels==rrels,(name,path,'RELATIONSHIP_CHANGED');relations+=len(lrels)
            meshes+=prim.IsA(UsdGeom.Mesh)
        checks.append(dict(path=name,outcome='PASS',source_sha256=sha(source),portable_sha256=sha(target),prims=len(original),meshes=meshes,attributes=attributes,relationships=relations,up_axis='Z',meters_per_unit=1))
        print('RELOCATED_STAGE_EQUIVALENT',name,len(original),attributes,flush=True)
    write(a.bundle/'relocation_verification.json',dict(outcome='PASS',roots=checks,scope='Actual directory relocation; exact composed prim/property/time-sample/relationship equality to tested sources, asset-content equality, stage units/defaultPrim and fully internal dependency closure. Not an additional dynamics simulation.'))
    print('PUBLIC_PACKAGE_RELOCATION_AND_SEMANTIC_EQUIVALENCE_PASS',len(checks))

if __name__=='__main__':main()
