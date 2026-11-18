"""Refresh metadata-only handoff and batch counts from current pinned registry evidence."""
from library import ROOT, read, write, summarize

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--active-batch',default='rigid005_006_offline_qualification')
    parser.add_argument('--evidence',default='reports/expansion_verification.json')
    args=parser.parse_args()
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
    progress=read(ROOT/'registry/batch_progress.json');progress.update(active_batch=args.active_batch,local_pool_target=150,counts={k:status[k] for k in (
        'candidates','acquired','converted','local_technical_ready','generation_ready','public_starter')})
    for target in status['batch_milestones']:
        if not any(m['target']==target for m in progress['milestones']):
            progress['milestones'].append(dict(target=target,outcome='PENDING'))
    progress['milestones'].sort(key=lambda m:m['target'])
    for milestone in progress['milestones']:
        target=milestone['target']
        if status['local_technical_ready']>=target:
            milestone.update(outcome='LOCAL_TECHNICAL_MILESTONE_ACHIEVED',actual=status['local_technical_ready'],evidence=args.evidence)
            milestone.pop('config',None)
        else:milestone.update(outcome='IN_PROGRESS_FROM_ACQUIRED_POOL' if target==next((t for t in status['batch_milestones'] if t>status['local_technical_ready']),150) else 'PENDING')
    status_paths=sorted((ROOT/'sources').glob('batch_*_*/batch_status.json'),key=lambda p:p.stat().st_mtime)
    pointer_path=ROOT/'registry/official_acquisition_latest.json'
    pointer=read(pointer_path) if pointer_path.exists() else {}
    latest=ROOT/pointer['status'] if pointer else status_paths[-1]
    assert latest.resolve().is_relative_to(ROOT/'sources')
    acquisition=read(latest)
    progress['acquisition_sessions']=[dict(attempt=p.parent.name,outcome=read(p)['outcome'],saved=len(read(p).get('completed',[])),outcome_scope='LAST_SAVED_STATE_NOT_LIVE_PROCESS_PROOF') for p in status_paths]
    old=progress.get('acquisition')
    if old and old['attempt']!=latest.parent.name:
        history=progress.setdefault('acquisition_history',[])
        if not any(x['attempt']==old['attempt'] for x in history):history.append(old)
    progress['acquisition']=dict(attempt=latest.parent.name,outcome=acquisition['outcome'],
        new_source_receipts=len(acquisition['completed']),current_query=acquisition.get('query'),
        query_index=acquisition.get('index'),planned_query_count=acquisition.get('continuous',{}).get('query_count'),
        user_action_required=acquisition['outcome']=='HUMAN_REQUIRED')
    if pointer.get('monitor'):
        monitored=read(ROOT/pointer['monitor'])
        progress['acquisition'].update(outcome=monitored['outcome'],last_saved_outcome=acquisition['outcome'],
            monitor=pointer['monitor'],user_action_required=monitored.get('user_action_required',False))
    progress['latest_asset_previews']='rigid_expansion.html'
    progress['next_actions']=['Prioritize diverse rigid hotel props toward approximately150 local technical assets; soft-object physics deferred',
        'Resolve material and geometry blockers in independent attempts, preserving originals, prior qualifications and failures',
        'Expand rigid object types using the official add-on when acquired backlog is exhausted; do not count recolors as independent assets',
        'Keep unclear extractable/public rights blocked independently from local tests']
    write(ROOT/'registry/batch_progress.json',progress);write(ROOT/'reports/status.json',status)
    print('METADATA_AND_PROGRESS_REFRESHED',len(rows),status['local_technical_ready'])

if __name__=='__main__':main()
