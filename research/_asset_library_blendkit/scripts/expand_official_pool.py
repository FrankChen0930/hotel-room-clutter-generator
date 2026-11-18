"""Semantic pre-screen of already returned official metadata; no network/download loop."""
from datetime import datetime,timezone
from pathlib import Path
import copy
import shutil
from library import ROOT,read,write,sha,validate

snapshot=ROOT/'sources/intake_user_002/visible_search_results.json';results=read(snapshot)['results']
registry=read(ROOT/'registry/assets.json');template=next(x for x in registry['assets'] if x['source']['asset_base_id']=='fa971768-8e7e-49dd-93e5-c225b578899e')
chosen={'639cf1dc-24e8-46db-a181-6082910b72c2','6d5257a4-4fdf-421d-92b9-e77f941f5187','804cce47-eb45-4dbe-bb30-4bccebc0513b'}
known={x['source']['asset_base_id'] for x in registry['assets']};added=[];acquired=[]
for meta in results:
    base=meta['assetBaseId']
    if base not in chosen or base in known:continue
    assert meta.get('isFree') is True and meta.get('canDownload') is True and meta.get('assetType')=='model'
    a=copy.deepcopy(template);author=meta.get('author') or {}
    a.update(asset_id='bk-'+base,name=meta.get('displayName') or meta['name'],author=' '.join(str(author[k]) for k in ('firstName','lastName') if author.get(k)),
        situations=['arrival_unpacking','stayover_personal'],appearance_family='pending_distinct_backpack_review',geometry_identity=None,
        status='BLOCKED',last_completed_stage='DISCOVERED',state_id='default',dimensions_m=None,usd={},evidence={},
        physics=dict(mode='UNQUALIFIED',mass_kg=None,collision_proxy=None),blockers=['ACQUISITION_OR_QUALITY_PENDING','EXTRACTABLE_GENERATOR_RIGHTS_UNCLEARED'])
    a.pop('preparation',None);a.pop('local_qualification',None)
    a['source']=dict(provider='Blendkit',asset_base_id=base,version_id=None,metadata_version_id=meta['id'],
        url='https://www.blendkit.com/asset-gallery-detail/'+base+'/',plan='FREE',original_file=None,acquisition_method=None,receipt=None,
        metadata_snapshot=dict(path=str(snapshot.relative_to(ROOT)),sha256=sha(snapshot)),metadata_checked_date=datetime.now(timezone.utc).date().isoformat(),
        metadata_scope='Actual official GUI search result; semantic pre-screen only, geometry and appearance not accepted')
    a['discovery_quality']=dict(visual_acceptance='NOT_REVIEWED',uniqueness='SOURCE_ID_DISTINCT_GEOMETRY_UNVERIFIED',
        reason='Adult travel backpack suitable for arrival/stayover; further texture/material and visual family screening required')
    cache=ROOT/'sources/official_cache_user/models'
    matches=[p for p in cache.glob('*/*.blend') if meta['id'] in p.parent.name]
    if len(matches)==1:
        original=matches[0];folder=ROOT/'sources'/base/meta['id'];folder.mkdir(parents=True,exist_ok=False)
        dest=folder/'original.blend';shutil.copy2(original,dest)
        receipt=folder/'acquisition.json';write(receipt,dict(asset_base_id=base,version_id=meta['id'],original_sha256=sha(dest),
            method='OFFICIAL_USER_CLIENT_CACHE_RECOVERY',metadata_snapshot=a['source']['metadata_snapshot'],
            cache_file=dict(path=str(original.relative_to(ROOT)),sha256=sha(original)),scope='Acquisition only; model quality/conversion not accepted'))
        a['source'].update(version_id=meta['id'],acquisition_method='OFFICIAL_ADDON',original_file=dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest)),
            receipt=dict(path=str(receipt.relative_to(ROOT)),sha256=sha(receipt)),original_download_files=[dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest))])
        a['last_completed_stage']='ACQUIRED';acquired.append(a['asset_id'])
    registry['assets'].append(a);added.append(a['asset_id'])
validate(registry['assets']);write(ROOT/'registry/assets.json',registry)
write(ROOT/'reports/official_pool_batch_001.json',dict(added=added,recovered_acquired=acquired,
    scope='Already received official search/cache only; no extra network acquisition',
    excluded_search_hits=['Fantasy/cosplay backpack','Cartoon model','Standalone buckle','Very low-detail backpack pending visual evidence','Child-specific model deferred from initial adult pool'],
    next_search_priorities=['luggage','clothing','footwear','toiletries','personal_electronics'],
    qualification='All new records remain unconverted/unaccepted; no geometry variants counted as independent READY assets'))
print('POOL_ADDED',len(added),'ALREADY_OFFICIALLY_CACHED_ACQUIRED',len(acquired))
