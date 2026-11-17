"""Pin the real user-downloaded official cache file and its official GUI metadata."""
from pathlib import Path
import shutil
from library import ROOT,read,write,sha
from register_official_snapshot import register

base='fa971768-8e7e-49dd-93e5-c225b578899e'
metadata_path=ROOT/'sources/intake_user_002/visible_search_results.json'
metadata=next(x for x in read(metadata_path)['results'] if x['assetBaseId']==base)
probe=read(ROOT/'reports/cached_backpack_probe.json');original=ROOT/probe['source']
if metadata['id'] not in original.parent.name or sha(original)!=probe['sha256']:raise ValueError('CACHE_VERSION_IDENTITY_MISMATCH')
folder=ROOT/'sources'/base/metadata['id'];folder.mkdir(parents=True,exist_ok=False)
dest=folder/'original.blend';shutil.copy2(original,dest)
receipt_path=folder/'acquisition.json'
write(receipt_path,dict(asset_base_id=base,version_id=metadata['id'],original_sha256=sha(dest),
    method='OFFICIAL_ADDON_CACHE_RECOVERY',cache_file=dict(path=str(original.relative_to(ROOT)),sha256=sha(original)),
    official_metadata=dict(path=str(metadata_path.relative_to(ROOT)),sha256=sha(metadata_path)),
    gui_status=dict(path='sources/intake_user_002/session.json',sha256=sha(ROOT/'sources/intake_user_002/session.json')),
    scope='Model already acquired through official user-run operator. Recover cached original without network retry or invented embedded metadata.'))
snapshot=folder/'recovered_source.json'
write(snapshot,dict(outcome='OFFICIAL_MODEL_SAVED_PENDING_INTAKE',blend=str(dest.relative_to(ROOT)),source_sha256=sha(dest),
    collection='Grey Fabric Backpack with Leather',metadata=metadata,
    official_download_files=[dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest),bytes=dest.stat().st_size)],
    original_download_hash_status='PINNED',recovery='Official cache recovery; no source mesh/embedded metadata rewritten'))
a=register(snapshot,'bag','arrival_unpacking')
registry=read(ROOT/'registry/assets.json');a=next(x for x in registry['assets'] if x['source']['asset_base_id']==base)
a['source'].update(version_id=metadata['id'],acquisition_method='OFFICIAL_ADDON',
    original_file=dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest)),
    receipt=dict(path=str(receipt_path.relative_to(ROOT)),sha256=sha(receipt_path)))
converted=ROOT/'artifacts'/base/'convert_a000'
conversion=read(converted/'conversion.json');integrity=read(converted/'integrity.json')
assert conversion['outcome']==integrity['outcome']=='PASS'
a.update(status='BLOCKED',last_completed_stage='CONVERTED',state_id='lying_scan',appearance_family='grey_fabric_leather_backpack',
    geometry_identity=conversion['geometry_identity'],dimensions_m=integrity['dimensions_m'],
    usd=dict(path=str((converted/'asset.usdc').relative_to(ROOT)),sha256=sha(converted/'asset.usdc')),
    physics=dict(mode='STATIC_ONLY',mass_kg=None,collision_proxy=None),blockers=['EXTRACTABLE_USD_RIGHTS_UNCLEARED','NATIVE_VISUAL_SUPPORT_CATALOG_REPLAY_PENDING'])
for kind,filename in [('conversion','conversion.json'),('integrity','integrity.json')]:
    p=converted/filename;a['evidence'][kind]=dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
a['preparation']=dict(path=str((ROOT/'artifacts'/base/'prepare_a000/preparation.json').relative_to(ROOT)),sha256=sha(ROOT/'artifacts'/base/'prepare_a000/preparation.json'))
write(ROOT/'registry/assets.json',registry)
write(folder/'recovery_result.json',dict(outcome='PASS',asset_id=a['asset_id'],acquired=True,converted=True,generation_ready=False,source_sha256=sha(dest),usd_sha256=a['usd']['sha256']))
print('REAL_OFFICIAL_BACKPACK_ACQUIRED_CONVERTED',a['asset_id'])
