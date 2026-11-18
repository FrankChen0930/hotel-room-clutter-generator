"""Ingest completed official GUI batch originals. No network and no acceptance by file count."""
from pathlib import Path
import shutil
from uuid import UUID
from library import ROOT,read,write,sha,artifact_ok,validate
from hotel_metadata import enrich

def main():
    registry=read(ROOT/'registry/assets.json');by_id={a['source']['asset_base_id']:a for a in registry['assets']};added=[]
    for record_path in sorted((ROOT/'sources').glob('batch_*_*/*/*/official_source.json')):
        record=read(record_path);meta=record['metadata'];base=meta['assetBaseId'];version=meta['id'];UUID(base);UUID(version)
        if base in by_id and by_id[base]['source'].get('version_id'):continue
        if record['outcome']!='OFFICIAL_RAW_ACQUIRED' or meta.get('assetType')!='model' or meta.get('isFree') is not True:raise ValueError('OFFICIAL_FREE_MODEL_RECEIPT_REQUIRED')
        if not artifact_ok(record['original_file']):raise ValueError('OFFICIAL_ORIGINAL_CHANGED')
        license={'cc_zero':'CC0','royalty_free':'Royalty Free'}.get(meta.get('license'),'UNKNOWN')
        if license=='UNKNOWN':raise ValueError('KNOWN_LICENSE_REQUIRED')
        folder=ROOT/'sources'/base/version;folder.mkdir(parents=True,exist_ok=False)
        source=ROOT/record['original_file']['path'];dest=folder/'original.blend';shutil.copy2(source,dest)
        receipt=folder/'acquisition.json'
        write(receipt,dict(asset_base_id=base,version_id=version,original_sha256=sha(dest),method='OFFICIAL_ADDON_SERIALIZED_GUI_BATCH',
            source_receipt=dict(path=str(record_path.relative_to(ROOT)),sha256=sha(record_path)),scope='Acquisition proof; not quality, generator or public approval'))
        author=meta.get('author') or {};author_name=' '.join(str(author[k]) for k in ('firstName','lastName') if author.get(k)) or 'author_id:'+str(author.get('id','UNKNOWN'))
        job=record['job'];a=dict(asset_id='bk-'+base,name=meta.get('displayName') or meta['name'],author=author_name,category=job['category'],
            situations=[job['scenario']],batch_job=job,batch_id=record.get('batch_id','batch_001'),appearance_family='pending_'+job['category']+'_visual_review',geometry_identity=None,variant_of=None,
            state_id='default',status='BLOCKED',last_completed_stage='ACQUIRED',source=dict(provider='Blendkit',asset_base_id=base,version_id=version,
                url='https://www.blendkit.com/asset-gallery-detail/'+base+'/',plan='FREE',acquisition_method='OFFICIAL_ADDON',
                original_file=dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest)),original_download_files=[dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest))],
                receipt=dict(path=str(receipt.relative_to(ROOT)),sha256=sha(receipt)),metadata_snapshot=dict(path=str(record_path.relative_to(ROOT)),sha256=sha(record_path)),
                original_download_hash_status='PINNED',upstream_author=author_name),
            rights=dict(license=license,license_url='https://www.blendkit.com/docs/licenses/',terms_url='https://www.blendkit.com/terms-and-conditions-2026/',
                internal_use=True,extractable_usd=None,redistribution=None,requires_user_acquisition=True,decision='PENDING_EXTRACTABLE_USD_TERMS',decision_evidence=None,
                local_test_scope='CONTROLLED_WORKSPACE_NO_DISTRIBUTION',local_test_evidence=dict(path='reports/local_test_authorization.json',sha256=sha(ROOT/'reports/local_test_authorization.json'))),
            dimensions_m=None,physics=dict(mode='UNQUALIFIED',mass_kg=None,collision_proxy=None),usd={},evidence={},
            blockers=['REAL_MODEL_CONVERSION_AND_QUALITY_PENDING','EXTRACTABLE_GENERATOR_RIGHTS_UNCLEARED'],rejection_reason=None,
            discovery_quality=dict(visual_acceptance='NOT_REVIEWED',uniqueness='SOURCE_ID_DISTINCT_GEOMETRY_NOT_VERIFIED',site_dimensions=meta.get('dimensions_metadata',{})))
        if base in by_id:
            old=by_id[base];registry['assets'][registry['assets'].index(old)]=a
        else:registry['assets'].append(a)
        by_id[base]=a;added.append(a['asset_id'])
    for a in registry['assets']:enrich(a)
    validate(registry['assets']);write(ROOT/'registry/assets.json',registry)
    write(ROOT/'reports/batch_001_import_latest.json',dict(added=added,total_registered=len(registry['assets']),scope='Acquisition/metadata only; no new ready count inferred'))
    print('OFFICIAL_BATCH_IMPORTED',len(added),'TOTAL_REGISTERED',len(registry['assets']))

if __name__=='__main__':main()
