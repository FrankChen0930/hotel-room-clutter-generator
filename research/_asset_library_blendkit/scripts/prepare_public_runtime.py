"""Prepare an isolated native-room runtime from a permission-audited portable bundle."""
import argparse
import copy
import os
from pathlib import Path
import shutil
from library import ROOT,read,write,sha
import usd_sdk


def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source-config',type=Path,required=True);p.add_argument('--target-library-root',type=Path,required=True);a=p.parse_args()
    target=a.target_library_root.resolve();assert target.is_relative_to(ROOT.parent) and target!=ROOT and target.name=='_asset_library_blendkit'
    receipt=read(a.bundle/'package_manifest.json')
    assert receipt['redistribution']=='HOTEL705_USER_CONFIRMED_AUTHOR_LAB_PERMISSION_ONLY'
    cfg=target/'config/public_hotel705';assert not cfg.exists();cfg.mkdir(parents=True)
    data=target/'public_data';shutil.copytree(a.bundle,data)
    mapping={(ROOT.parent/row['source']).resolve():data/row['path'] for row in receipt['files']}
    usd_sdk.load()
    from pxr import UsdUtils,Usd,UsdGeom
    from integrate_real_backpack import load_inputs
    from common_core.identity import content_digest
    inputs=load_inputs(a.source_config/'deployment.json','hotel705')
    profile=copy.deepcopy(inputs.profile);policy=copy.deepcopy(inputs.policy);catalog=copy.deepcopy(inputs.catalog)
    old_room=Path(inputs.bindings[profile['source']['mount']])/profile['source']['path'];room=mapping[old_room.resolve()]
    def dependency_rows(path,mount,anchor):
        layers,assets,missing=UsdUtils.ComputeAllDependencies(str(path));assert not missing
        paths={Path(x.realPath).resolve() for x in layers}|{Path(str(x)).resolve() for x in assets}
        assert all(x.is_relative_to(data) for x in paths)
        return [dict(mount=mount,path=x.relative_to(anchor).as_posix(),sha256=sha(x),bytes=x.stat().st_size) for x in sorted(paths)]
    closure=dependency_rows(room,'room_hotel',data)
    profile['source'].update(path=room.relative_to(data).as_posix(),sha256=sha(room),bytes=room.stat().st_size,closure_sha256=content_digest(closure))
    profile['profile_version']='public-native-portable-20261119'
    catalog['version']='public-native-portable-20261119';assets={};native=[]
    original_rows={r['asset_id']:r for r in read(ROOT/'artifacts/legacy_density_pool_a001/index.json') if r['source_kind']=='EXISTING_ROOM_NOT_NEW_BLENDKIT'}
    assert {e['asset_id'] for e in catalog['entries']}==set(original_rows)
    for entry in catalog['entries']:
        old=Path(original_rows[entry['asset_id']]['usd_path']).resolve();path=mapping[old]
        locator=dict(mount='blendkit_library',path=path.relative_to(target).as_posix())
        deps=dependency_rows(path,'blendkit_library',target)
        entry.update(source_locator=locator,dependency_hashes=deps,qualification_refs=[])
        state=entry['states'][0];state.update(usd_locator_or_native_prim=locator,sha256=sha(path))
        state['physics_proxy']['geometry_hash']=sha(path)
        # Verify USD recoding did not alter the actual object dimensions.
        stage=Usd.Stage.Open(str(path));box=UsdGeom.BBoxCache(0,['default','render','proxy']).ComputeWorldBound(stage.GetDefaultPrim()).ComputeAlignedRange()
        dimensions=list(box.GetSize());assert max(abs(x-y) for x,y in zip(dimensions,entry['dimensions']))<1e-5
        entry['provenance']=dict(kind='HOTEL705_NATIVE_PROP_PORTABLE_DERIVATIVE',original_sha256=sha(old),human_confirmed=True)
        for row in deps:assets[row['path']]=row
        native.append(dict(asset_id=entry['asset_id'],category=entry['category'],dimensions_m=entry['dimensions'],state_id='default',
            source_kind='EXISTING_ROOM_NOT_NEW_BLENDKIT',usd_path_relative=locator['path']))
    lock=dict(schema_version='1.0',rooms=dict(room_hotel=dict(root={k:profile['source'][k] for k in ['mount','path','sha256','bytes']},closure=closure,unresolved=[],closure_verified=True)),
        helpers=[],environment=copy.deepcopy(inputs.source_lock.get('environment',{})),assets=list(assets.values()))
    deployment=dict(bindings=dict(room_hotel=os.path.relpath(data,cfg).replace('\\','/'),blendkit_library=os.path.relpath(target,cfg).replace('\\','/')),
        rooms=dict(hotel705='profile.json'),catalog='catalog.json',policy='policy.json',source_lock='source_lock.json')
    for name,value in [('deployment.json',deployment),('profile.json',profile),('policy.json',policy),('catalog.json',catalog),('source_lock.json',lock)]:write(cfg/name,value)
    write(target/'artifacts/legacy_density_pool_a001/index.json',native)
    write(target/'registry/assets.json',dict(schema_version='1.0',assets=[]))
    permission=read(ROOT/'reports/hotel705_redistribution_permission_20261118.json');write(target/'reports/hotel705_redistribution_permission_20261118.json',permission)
    cameras=read(ROOT/'runs/measured_surfaces_a002/render_batch.json')['cases'][0]['cameras']
    write(target/'runs/measured_surfaces_a002/render_batch.json',dict(cases=[dict(cameras=cameras)],scope='Camera metadata only; no historical scene or evidence is reproduced here'))
    for directory in ['_common_core_runs','_common_core_planning']:
        (target.parent/directory).mkdir(exist_ok=True)
        (target.parent/directory/'README.md').write_text('Public runtime boundary and metadata directory. Original private research runs are not bundled.\n',encoding='utf-8')
    inventory=[dict(path=f.relative_to(target).as_posix(),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(data.rglob('*')) if f.is_file()]
    write(target/'config/public_source_inventory.json',dict(files=inventory,scope='Immutable packaged Hotel705/native source data; no Blendkit assets'))
    checked=load_inputs(cfg/'deployment.json','hotel705');assert len(checked.catalog['entries'])==5
    write(target/'reports/portable_runtime_preparation.json',dict(outcome='CONFIG_CATALOG_SOURCE_LOAD_PASS',source_files=len(inventory),native_source_records=5,
        scope='Portable relative bindings, dependency pins and real USD dimensions verified; new generation and physics execution remain required.'))
    print('PUBLIC_RUNTIME_CONFIG_LOAD_PASS',len(inventory))


if __name__=='__main__':main()
