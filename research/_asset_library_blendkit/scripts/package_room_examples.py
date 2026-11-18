"""Build a private portable USD dependency closure; this grants no redistribution rights."""
import argparse
import os
from pathlib import Path
import shutil
import sys
from library import ROOT, read, write, sha
import usd_sdk


def package(roots, output):
    usd_sdk.load()
    from pxr import Sdf, Usd, UsdUtils, UsdGeom
    output=Path(output).resolve()
    assert output.is_relative_to(ROOT.parent) and not output.exists()
    sources={};layers={}
    for label,path in roots.items():
        path=Path(path).resolve(strict=True)
        assert path.is_relative_to(ROOT.parent)
        found,assets,unresolved=UsdUtils.ComputeAllDependencies(str(path))
        assert not unresolved,('SOURCE_DEPENDENCIES_MISSING',list(map(str,unresolved)))
        for layer in found:
            origin=Path(layer.realPath).resolve(strict=True)
            assert origin.is_relative_to(ROOT.parent),('SOURCE_OUTSIDE_WORKSPACE',origin)
            layers[origin]=layer;sources[origin]=None
        for asset in assets:
            origin=Path(str(asset)).resolve(strict=True)
            assert origin.is_relative_to(ROOT.parent),('ASSET_OUTSIDE_WORKSPACE',origin)
            sources[origin]=None
        sources[path]=None
    output.mkdir(parents=True)
    (output/'assets').mkdir()
    import hashlib
    for origin in sources:
        # Path identity preserves distinct relative-resolution contexts for equal layer bytes.
        identity=hashlib.sha256(str(origin).encode()).hexdigest()[:16]
        sources[origin]=output/'assets'/(identity+('.usdc' if origin in layers else origin.suffix.lower()))
    inventory=[]
    for origin,target in sources.items():
        before=sha(origin)
        if origin in layers:
            original=layers[origin];copy=Sdf.Layer.CreateAnonymous()
            copy.TransferContent(original)
            def relocate(value):
                if not value:return value
                resolved=Path(Sdf.ComputeAssetPathRelativeToLayer(original,value)).resolve()
                assert resolved in sources,('UNMAPPED_ASSET_PATH',str(origin),value,str(resolved))
                return os.path.relpath(sources[resolved],target.parent).replace('\\','/')
            UsdUtils.ModifyAssetPaths(copy,relocate)
            assert copy.Export(str(target))
        else:shutil.copy2(origin,target)
        assert sha(origin)==before,'ORIGINAL_CHANGED'
        inventory.append(dict(source=str(origin.relative_to(ROOT.parent)),source_sha256=before,
            path=target.relative_to(output).as_posix(),sha256=sha(target),bytes=target.stat().st_size,
            derivative='RELATIVE_PATH_USDC_REENCODING' if origin in layers else 'BYTE_IDENTICAL_DEPENDENCY'))
    checks=[]
    for label,path in roots.items():
        root=output/label;root.parent.mkdir(parents=True,exist_ok=True)
        layer=Sdf.Layer.CreateNew(str(root));layer.subLayerPaths=[os.path.relpath(sources[Path(path).resolve()],root.parent).replace('\\','/')];layer.Save()
        stage=Usd.Stage.Open(str(root));assert stage and any(stage.Traverse())
        original_stage=Usd.Stage.Open(str(path))
        # Stage-level metadata is read from the root layer, not inherited from sublayers.
        UsdGeom.SetStageUpAxis(stage,UsdGeom.GetStageUpAxis(original_stage))
        UsdGeom.SetStageMetersPerUnit(stage,UsdGeom.GetStageMetersPerUnit(original_stage))
        for key in ['timeCodesPerSecond','framesPerSecond','startTimeCode','endTimeCode']:
            value=original_stage.GetMetadata(key)
            if value is not None:stage.SetMetadata(key,value)
        original_default=original_stage.GetDefaultPrim()
        if original_default:stage.SetDefaultPrim(stage.GetPrimAtPath(original_default.GetPath()))
        stage.GetRootLayer().Save()
        assert UsdGeom.GetStageUpAxis(stage)==UsdGeom.GetStageUpAxis(original_stage)
        assert UsdGeom.GetStageMetersPerUnit(stage)==UsdGeom.GetStageMetersPerUnit(original_stage)
        assert bool(stage.GetDefaultPrim())==bool(original_default)
        found,assets,unresolved=UsdUtils.ComputeAllDependencies(str(root));assert not unresolved
        actual=[Path(x.realPath).resolve() for x in found]+[Path(str(x)).resolve() for x in assets]
        assert all(x.is_relative_to(output) for x in actual),'EXTERNAL_DEPENDENCY_REMAINS'
        checks.append(dict(path=label,sha256=sha(root),layers=len(found),assets=len(assets),outcome='PASS',
            up_axis=UsdGeom.GetStageUpAxis(stage),meters_per_unit=UsdGeom.GetStageMetersPerUnit(stage),
            default_prim=str(stage.GetDefaultPrim().GetPath()) if stage.GetDefaultPrim() else None))
    receipt=dict(outcome='LOCAL_PORTABLE_CLOSURE_PASS',roots=checks,files=inventory,
        redistribution='NOT_CLEARED_DO_NOT_UPLOAD_BINARY_BUNDLE',
        scope='Private dependency-closed USD package. Source files unchanged. No license or dynamics promotion. Physics/manifests delivered separately.')
    write(output/'package_manifest.json',receipt)
    return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--hotel705-permission',action='store_true');p.add_argument('--clean-scene',type=Path);p.add_argument('--clean-physics-receipt',type=Path);a=p.parse_args()
    cases=read(a.run/'cases.json')['cases'];assert len(cases)==6 and read(a.run/'verification.json')['outcome']=='PASS'
    from integrate_real_backpack import load_inputs
    inputs=load_inputs(Path(cases[0]['config']),'hotel705')
    profile=inputs.profile
    clean=Path(inputs.bindings[profile['source']['mount']])/profile['source']['path']
    roots={'clean_room.usda':clean}
    if a.clean_scene:
        assert a.clean_physics_receipt
        physics=read(a.clean_physics_receipt)
        assert physics['outcome']=='DIAGNOSTIC_PASS' and physics['registered_dynamic_bodies']==49 and physics['authored_joints']==31 and physics['native_steps']==3600
        assert physics['source_sha256']==sha(a.clean_scene) and read(a.clean_scene.parent/'geometry_preservation.json')['outcome']=='PASS'
        roots['clean_room.usda']=a.clean_scene
    for c in cases:
        stem=f"scenes/{c['level']}_seed_{c['seed']}"
        roots[stem+'.usda']=c['scene'];roots[stem+'_dynamic.usda']=c['dynamic_scene']
    report=package(roots,a.output)
    if a.hotel705_permission:
        permission=ROOT/'reports/hotel705_redistribution_permission_20261118.json'
        assert read(permission)['outcome']=='USER_CONFIRMED_PERMISSION'
        allowed={r['asset_id'] for r in read(ROOT/'artifacts/legacy_density_pool_a001/index.json') if r['source_kind']=='EXISTING_ROOM_NOT_NEW_BLENDKIT'}
        for case in cases:
            assert case.get('pool_scope')=='HOTEL705_ORIGINAL_PROPS_ONLY_LIMITED_DIVERSITY'
            assert {o['asset_id'] for o in read(case['manifest'])['objects']}<=allowed
        from pxr import UsdUtils
        allowed_sources=set()
        for source in [clean,*[Path(r['usd_path']) for r in read(ROOT/'artifacts/legacy_density_pool_a001/index.json') if r['asset_id'] in allowed]]:
            ls,assets,unresolved=UsdUtils.ComputeAllDependencies(str(source));assert not unresolved
            allowed_sources.update(Path(x.realPath).resolve() for x in ls);allowed_sources.update(Path(str(x)).resolve() for x in assets)
        for row in report['files']:
            source=(ROOT.parent/row['source']).resolve()
            assert source in allowed_sources or source.is_relative_to(ROOT/'runs'),('UNAPPROVED_EXTERNAL_ASSET',source)
        report.update(redistribution='HOTEL705_USER_CONFIRMED_AUTHOR_LAB_PERMISSION_ONLY',permission_sha256=sha(permission),
            limitations='Original-room native props only, limited diversity; no Blendkit assets or blanket public license. User confirmation is the permission record.')
        write(a.output/'package_manifest.json',report)
    print('PRIVATE_ROOM_PACKAGE_CLOSURE_PASS',len(report['roots']),len(report['files']))


if __name__=='__main__':main()
