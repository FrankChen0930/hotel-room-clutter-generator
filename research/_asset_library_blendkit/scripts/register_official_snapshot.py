"""Register factual metadata from a human-selected official download; never fetch models."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from library import ROOT, read, write, sha, local, validate

def register(snapshot_path,category,situation):
    snapshot_path=Path(snapshot_path).resolve(strict=True)
    if not snapshot_path.is_relative_to(ROOT/'sources'):raise ValueError('PRIVATE_WORKSPACE_SNAPSHOT_REQUIRED')
    snapshot=read(snapshot_path)
    if snapshot.get('outcome')!='OFFICIAL_MODEL_SAVED_PENDING_INTAKE':raise ValueError('NOT_COMPLETED_OFFICIAL_DOWNLOAD')
    data=snapshot['metadata'];base=data['assetBaseId'];version=data['id'];UUID(base);UUID(version)
    if data.get('isFree') is not True or data.get('assetType')!='model':raise ValueError('FREE_MODEL_REQUIRED')
    source=local(snapshot['blend'])
    if not source.is_file() or sha(source)!=snapshot['source_sha256']:raise ValueError('DOWNLOADED_SOURCE_CHANGED')
    license={'cc_zero':'CC0','royalty_free':'Royalty Free'}.get(data.get('license'),'UNKNOWN')
    author=data.get('author') or {};name=' '.join(str(author[k]).strip() for k in ('firstName','lastName') if author.get(k)).strip()
    if not name:raise ValueError('AUTHOR_METADATA_MISSING_REVIEW_BEFORE_REGISTRATION')
    registry=read(ROOT/'registry/assets.json');validate(registry['assets'])
    existing=[a for a in registry['assets'] if a['source']['asset_base_id']==base]
    if existing:
        a=existing[0]
        if a['source'].get('version_id'):raise ValueError('SOURCE_ALREADY_ACQUIRED_NO_DUPLICATE_COUNT')
        if a['status']=='REJECTED':raise ValueError('REJECTED_SOURCE_REQUIRES_REVIEW')
    else:
        a=dict(asset_id='bk-'+base,name=data.get('displayName') or data.get('name'),author=name,category=category,
            situations=[situation],appearance_family=category+'_pending_visual_review',geometry_identity=None,variant_of=None,
            state_id='default',status='DISCOVERED',last_completed_stage='DISCOVERED',
            source=dict(provider='Blendkit',asset_base_id=base,version_id=None,url='https://www.blendkit.com/asset-gallery-detail/'+base+'/',
                original_file=None,acquisition_method=None,receipt=None,plan='FREE'),
            rights={},dimensions_m=None,physics=dict(mode='UNQUALIFIED',mass_kg=None,collision_proxy=None),usd={},evidence={},
            blockers=['EXTRACTABLE_USD_RIGHTS_UNCLEARED'],rejection_reason=None)
        registry['assets'].append(a)
    evidence=dict(path=str(snapshot_path.relative_to(ROOT)),sha256=sha(snapshot_path))
    a['name']=data.get('displayName') or data.get('name');a['author']=name
    a['blockers']=[x for x in a.get('blockers',[]) if x!='PAID_PLAN_NOT_AUTHORIZED'
        and not (license!='UNKNOWN' and x=='DETAIL_PAGE_LICENSE_AUTHOR_NOT_VERIFIED')]
    a['source'].update(metadata_checked_date=datetime.now(timezone.utc).date().isoformat(),plan='FREE',
        metadata_scope='Sanitized metadata of human-selected download through official GUI',metadata_snapshot=evidence,
        original_download_files=snapshot.get('official_download_files',[]),
        original_download_hash_status=snapshot.get('original_download_hash_status','PENDING_LOCATE_OFFICIAL_CACHE'))
    a['rights'].update(license=license,license_url='https://www.blendkit.com/docs/licenses/',
        terms_url='https://www.blendkit.com/terms-and-conditions-2026/',internal_use=True if license!='UNKNOWN' else None,
        extractable_usd=None,redistribution=None,requires_user_acquisition=True,decision='PENDING_EXTRACTABLE_USD_TERMS',
        decision_evidence=None,local_test_scope='CONTROLLED_WORKSPACE_NO_DISTRIBUTION',
        local_test_evidence=dict(path='reports/local_test_authorization.json',sha256=sha(ROOT/'reports/local_test_authorization.json')))
    a['discovery_quality']=dict(visual_acceptance='PENDING',metadata_snapshot=evidence,uniqueness='SOURCE_ID_ONLY_GEOMETRY_REVIEW_PENDING')
    validate(registry['assets']);write(ROOT/'registry/assets.json',registry)
    print('REGISTERED_OFFICIAL_METADATA',a['asset_id'],license,'NEXT intake_blender.py collection:',snapshot['collection'])
    return a

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--category',required=True);p.add_argument('--situation',required=True)
    args=p.parse_args();register(args.snapshot,args.category,args.situation)
