"""Reuse the validated Core candidate adapter for new assets; skip completed cases."""
import os
from pathlib import Path
import subprocess
import sys
from library import ROOT,read,write

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--pending-only',action='store_true');p.add_argument('--cohort',default='batch_001');p.add_argument('--base-ids',nargs='+');args=p.parse_args()
    records={a['source']['asset_base_id']:a for a in read(ROOT/'registry/assets.json')['assets']}
    jobs=read(ROOT/'config/batch_001_processing_jobs.json')['jobs'];cases=[];failures=[]
    for job in jobs:
        base=job['base_id'];tag=job['tag'];converted=ROOT/job['conversion_dir']
        if args.base_ids and base not in args.base_ids:continue
        record=records[base]
        if record['status']=='REJECTED' or (args.pending_only and record.get('local_qualification',{}).get('outcome')=='PASS'):continue
        if not (converted/'integrity.json').is_file() or read(converted/'integrity.json')['outcome']!='PASS':continue
        run=ROOT/('runs/real_backpack_hotel705_stayover_high_706_'+tag);index=run/'case_index.json'
        if not index.exists():
            command=[sys.executable,'-B',str(ROOT/'scripts/integrate_real_backpack.py'),'--tag',tag,'--base-id',base,
                '--conversion-dir',str(converted),'--state',job['state_id'],'--supports',*job['supports']]
            if job.get('replace_request_ids'):command+=['--replace-request-ids',*job['replace_request_ids']]
            log=ROOT/'reports'/('case_'+tag+'.log')
            with log.open('x',encoding='utf-8') as stream:
                result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONIOENCODING':'utf-8'},stdout=stream,stderr=subprocess.STDOUT,timeout=240)
            if result.returncode!=0:
                failures.append(dict(asset_id='bk-'+base,reason='CORE_CANDIDATE_CASE_FAILED',log=str(log.relative_to(ROOT))));continue
        cases.append(read(index));print('REAL_BATCH_CASE',base,'STATIC_REPLAY_COMPLETE',flush=True)
    second=ROOT/'runs/real_backpack_hotel705_stayover_high_706_batch001_02/case_index.json'
    if second.is_file() and not args.pending_only:cases.insert(0,read(second))
    write(ROOT/'config'/(args.cohort+'_cases.json'),dict(cases=cases,failures=failures))
    write(ROOT/'config'/(args.cohort+'_preview_jobs.json'),dict(jobs=[dict(asset_id=c['asset_id'],usd=c['asset']) for c in cases]))
    print('NEW_REAL_CASES',len(cases),'BLOCKED',len(failures))

if __name__=='__main__':main()
