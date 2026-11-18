"""Expand discovery from already returned official GUI results; no network calls."""
from collections import Counter
from library import ROOT,read,write,sha,validate
from batch_selection import assess
from hotel_metadata import enrich

def main():
    registry=read(ROOT/'registry/assets.json');known={a['source']['asset_base_id'] for a in registry['assets']}
    added=[];decisions=[]
    for snapshot in sorted((ROOT/'sources').glob('batch_*_*/*_results.json')):
        data=read(snapshot);job=data['query']
        for meta in data['results']:
            base=meta.get('assetBaseId');score,reason=assess(meta,job['category'])
            decisions.append(dict(asset_base_id=base,name=meta.get('displayName') or meta.get('name'),category=job['category'],reason=reason))
            if score is None or base in known:continue
            author=meta.get('author') or {};author_name=' '.join(str(author[k]) for k in ('firstName','lastName') if author.get(k)) or 'author_id:'+str(author.get('id','UNKNOWN'))
            a=dict(asset_id='bk-'+base,name=meta.get('displayName') or meta['name'],author=author_name,category=job['category'],
                situations=[job['scenario']],batch_job=job,batch_id='batch_001',appearance_family='pending_'+base,geometry_identity=None,variant_of=None,
                state_id='default',status='DISCOVERED',last_completed_stage='DISCOVERED',
                source=dict(provider='Blendkit',asset_base_id=base,version_id=None,metadata_version_id=meta['id'],
                    url='https://www.blendkit.com/asset-gallery-detail/'+base+'/',plan='FREE',acquisition_method=None,original_file=None,receipt=None,
                    metadata_snapshot=dict(path=str(snapshot.relative_to(ROOT)),sha256=sha(snapshot))),
                rights=dict(license={'cc_zero':'CC0','royalty_free':'Royalty Free'}[meta['license']],license_url='https://www.blendkit.com/docs/licenses/',
                    terms_url='https://www.blendkit.com/terms-and-conditions-2026/',internal_use=None,extractable_usd=None,redistribution=None,
                    requires_user_acquisition=True,decision='PENDING_EXTRACTABLE_USD_TERMS',decision_evidence=None),
                dimensions_m=None,physics=dict(mode='UNQUALIFIED',mass_kg=None,collision_proxy=None),usd={},evidence={},
                blockers=['OFFICIAL_ACQUISITION_AND_VISUAL_REVIEW_PENDING'],rejection_reason=None,
                discovery_quality=dict(visual_acceptance='NOT_REVIEWED',uniqueness='DISTINCT_SOURCE_ID_ONLY',reason=reason))
            enrich(a);registry['assets'].append(a);known.add(base);added.append(a['asset_id'])
    validate(registry['assets']);write(ROOT/'registry/assets.json',registry)
    write(ROOT/'reports/batch001_candidate_screening.json',dict(added=added,decisions=decisions,
        decision_counts=dict(Counter(x['reason'] for x in decisions)),scope='Existing official search snapshots only; source-ID discovery is not geometric uniqueness or usable acceptance'))
    print('NEW_OFFICIAL_METADATA_CANDIDATES',len(added),'TOTAL',len(registry['assets']))

if __name__=='__main__':main()
