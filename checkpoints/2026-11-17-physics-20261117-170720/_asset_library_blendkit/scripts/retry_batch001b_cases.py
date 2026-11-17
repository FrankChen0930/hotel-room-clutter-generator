"""Bounded region/activity corrections after logged occupancy failures."""
import os
import subprocess
import sys
from library import ROOT,read,write

fixes=[('05678a43-b5dc-4c2f-b545-1ed650c52c19',['floor_luggage'],[]),
('b147eaa3-47f4-4882-82b4-e338d8d84bb1',['bench'],['quality/s0_towel/1']),
('4f737a79-e12c-4fd5-8447-65b5abbae793',['desk'],['quality/book/0']),
('e65f0387-6b19-49fe-981c-9dcdde602d1a',['floor_luggage'],[])]
if __name__=='__main__':
    cases=read(ROOT/'config/batch001b_cases.json')['cases'];failed=[]
    for base,supports,replaces in fixes:
        tag='batch001_'+base[:8]+'_a001';run=ROOT/('runs/real_backpack_hotel705_stayover_high_706_'+tag);index=run/'case_index.json'
        if not index.exists():
            command=[sys.executable,'-B',str(ROOT/'scripts/integrate_real_backpack.py'),'--tag',tag,'--base-id',base,'--conversion-dir',str(ROOT/'artifacts'/base/'convert_batch001'),'--state','source_fixed_form','--supports',*supports]
            if replaces:command+=['--replace-request-ids',*replaces]
            with (ROOT/'reports'/('case_'+tag+'.log')).open('x',encoding='utf-8') as stream:
                rc=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONIOENCODING':'utf-8'},stdout=stream,stderr=subprocess.STDOUT,timeout=240).returncode
            if rc:failed.append(dict(asset_id='bk-'+base,reason='BOUNDED_REGION_RETRY_FAILED'));continue
        cases.append(read(index));print('NEW_REGION_CASE_PASS',base,flush=True)
    write(ROOT/'config/batch001c_cases.json',dict(cases=cases,failures=failed))
    write(ROOT/'config/batch001c_preview_jobs.json',dict(jobs=[dict(asset_id=c['asset_id'],usd=c['asset']) for c in cases if any(c['asset_id']=='bk-'+f[0] for f in fixes)]))
