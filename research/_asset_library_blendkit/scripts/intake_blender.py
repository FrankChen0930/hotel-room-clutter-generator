"""Register an officially downloaded, dedicated packed .blend. No asset download API."""
import bpy
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT, sha, read, write, validate
from asset_dependencies import linked_asset_datablocks

def main():
    args=sys.argv[sys.argv.index('--')+1:]
    source=Path(args[0]).resolve(strict=True); collection_name=args[1]
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    col=bpy.data.collections.get(collection_name)
    if not col: raise ValueError('EXACT_COLLECTION_REQUIRED')
    payloads=[]
    for owner in [col,*col.all_objects]:
        data=owner.get('asset_data')
        if data and data.get('assetBaseId') and data.get('id'): payloads.append(data)
    identities={(d['assetBaseId'],d['id']) for d in payloads}
    if len(identities)!=1: raise ValueError('ONE_OFFICIAL_ASSET_METADATA_ID_REQUIRED')
    base,version=next(iter(identities)); data=payloads[0]
    if linked_asset_datablocks(col.all_objects): raise ValueError('ASSET_LINKED_DEPENDENCIES_REQUIRE_LOCAL_PACKED_SOURCE')
    if any(im.type=='IMAGE' and im.source=='FILE' and not im.packed_file for im in bpy.data.images):
        raise ValueError('PACK_ALL_EXTERNAL_IMAGES_IN_DEDICATED_DOWNLOAD_BLEND_FIRST')
    registry=read(ROOT/'registry/assets.json'); validate(registry['assets'])
    matches=[a for a in registry['assets'] if a['source']['asset_base_id']==base]
    if len(matches)!=1: raise ValueError('REGISTER_DISCOVERY_WITH_SOURCE_AUTHOR_LICENSE_FIRST')
    a=matches[0]
    if a['status']=='REJECTED': raise ValueError('REJECTED_CANDIDATE')
    if a['source'].get('version_id'): raise ValueError('ALREADY_ACQUIRED_USE_NEW_VERSION_REVIEW')
    folder=ROOT/'sources'/base/version; folder.mkdir(parents=True,exist_ok=False)
    dest=folder/'original.blend'; shutil.copy2(source,dest)
    # Keep source bytes in the library, independent of the official client's mutable cache.
    raw=a['source'].get('original_download_files',[])
    preserved=[]
    from library import artifact_ok,local
    for index,record in enumerate(raw):
        if not artifact_ok(record):raise ValueError('OFFICIAL_RAW_DOWNLOAD_MISSING_OR_CHANGED')
        raw_path=local(record['path']);raw_copy=folder/('downloaded_original_'+str(index)+raw_path.suffix)
        shutil.copy2(raw_path,raw_copy)
        preserved.append(dict(path=str(raw_copy.relative_to(ROOT)),sha256=sha(raw_copy)))
    a['source']['cache_origin_files']=raw
    a['source']['original_download_files']=preserved
    receipt=folder/'acquisition.json'
    write(receipt,dict(asset_base_id=base,version_id=version,original_sha256=sha(dest),
        method='OFFICIAL_ADDON_METADATA_IN_PACKED_BLEND',collection=collection_name,
        metadata_license=str(data.get('license','UNKNOWN')),
        scope='Identity evidence from local official-add-on metadata; not independent proof of authorship or legal clearance'))
    a['source'].update(version_id=version,acquisition_method='OFFICIAL_ADDON',
        original_file=dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest)),
        receipt=dict(path=str(receipt.relative_to(ROOT)),sha256=sha(receipt)))
    a['last_completed_stage']='ACQUIRED'; a['status']='BLOCKED'
    a['blockers']=[x for x in a['blockers'] if x!='OFFICIAL_ACQUISITION_UNAVAILABLE']
    if not a['blockers']: a['status']='ACQUIRED'
    raw=a['source'].get('original_download_files',[])
    from library import artifact_ok
    if not raw or not all(artifact_ok(ref) for ref in raw):
        a['status']='BLOCKED'
        if 'ORIGINAL_DOWNLOAD_HASH_PENDING' not in a['blockers']:a['blockers'].append('ORIGINAL_DOWNLOAD_HASH_PENDING')
    else:a['source']['original_download_hash_status']='PINNED'
    validate(registry['assets']); write(ROOT/'registry/assets.json',registry)
    print('ACQUIRED_LOCAL_SOURCE',base,version,'USD rights and quality gates remain separate')

if __name__=='__main__': main()
