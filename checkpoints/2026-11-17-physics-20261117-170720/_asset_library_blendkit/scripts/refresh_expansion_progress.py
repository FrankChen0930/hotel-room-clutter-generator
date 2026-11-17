"""Refresh metadata-only handoff and batch counts from current pinned registry evidence."""
from library import ROOT, read, write, summarize

def main():
    assets=read(ROOT/'registry/assets.json')['assets'];status=summarize(assets)
    previous=read(ROOT/'registry/retrieval_manifest.json')
    rows=[]
    for a in assets:
        source=a['source'];original=source.get('original_file')
        if not original:continue
        rights=a['rights']
        rows.append(dict(asset_id=a['asset_id'],asset_base_id=source['asset_base_id'],version_id=source['version_id'],
            name=a['name'],author=source.get('upstream_author'),source_url=source['url'],license=rights['license'],
            original_sha256=original['sha256'],local_test_eligible=rights.get('internal_use') is True,
            extractable_generator_eligible=rights.get('extractable_usd'),public_redistribution_eligible=rights.get('redistribution'),
            requires_own_official_acquisition=rights.get('requires_user_acquisition',True),quality_decision=a['quality_decision']))
    previous.update(assets=rows,public_asset_payloads=[])
    write(ROOT/'registry/retrieval_manifest.json',previous)
    progress=read(ROOT/'registry/batch_progress.json');progress.update(active_batch='batch_004_offline_qualification',counts={k:status[k] for k in (
        'candidates','acquired','converted','local_technical_ready','generation_ready','public_starter')})
    for milestone in progress['milestones']:
        target=milestone['target']
        if status['local_technical_ready']>=target:
            milestone.update(outcome='LOCAL_TECHNICAL_MILESTONE_ACHIEVED',actual=status['local_technical_ready'],evidence='reports/expansion_verification.json')
            milestone.pop('config',None)
        else:milestone.update(outcome='IN_PROGRESS_FROM_ACQUIRED_POOL' if target==50 else 'PENDING')
    acquisition=read(ROOT/'sources/batch_003_001/batch_status.json')
    progress['acquisition']=dict(attempt='batch_003_001',outcome=acquisition['outcome'],new_source_receipts=len(acquisition['completed']),user_action_required=False)
    progress['next_actions']=['Inspect and process remaining hotel-suitable acquired sources toward 50','Resolve material and scan-background blockers in independent attempts, preserving originals and failures','Keep unclear extractable/public rights blocked independently from local tests']
    write(ROOT/'registry/batch_progress.json',progress);write(ROOT/'reports/status.json',status)
    print('METADATA_AND_PROGRESS_REFRESHED',len(rows),status['local_technical_ready'])

if __name__=='__main__':main()
