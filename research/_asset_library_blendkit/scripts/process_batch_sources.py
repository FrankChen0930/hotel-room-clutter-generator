"""Process only new real source jobs, preserving each attempt and every failure."""
import os
from pathlib import Path
import subprocess
import sys
from library import ROOT,read,write,sha
from hotel_metadata import enrich

BLENDER='C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
ENV={**os.environ,'BLENDER_USER_RESOURCES':str(ROOT/'blender_profile'),
    'BLENDER_USER_CONFIG':str(ROOT/'blender_profile/config'),'BLENDER_USER_SCRIPTS':str(ROOT/'blender_profile/scripts'),
    'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'}
def blender(script,argument,log):
    with log.open('x',encoding='utf-8') as stream:
        result=subprocess.run([BLENDER,'--background','--factory-startup','--disable-autoexec','--python-exit-code','1',
            '--python',str(ROOT/'scripts'/script),'--',str(argument)],cwd=ROOT,env=ENV,stdout=stream,stderr=subprocess.STDOUT,timeout=150)
    return result.returncode

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--base-ids',nargs='+');args=p.parse_args()
    from inspect_usd import inspect
    outcomes=[]
    for job in read(ROOT/'config/batch_001_processing_jobs.json')['jobs']:
        if args.base_ids and job['base_id'] not in args.base_ids:continue
        record=next(x for x in read(ROOT/'registry/assets.json')['assets'] if x['source']['asset_base_id']==job['base_id'])
        if record['status']=='REJECTED':continue
        base=job['base_id'];folder=ROOT/'artifacts'/base;folder.mkdir(parents=True,exist_ok=True)
        converted=ROOT/job['conversion_dir'];prepared=ROOT/job['prepare_dir']
        if (converted/'integrity.json').is_file() and read(converted/'integrity.json')['outcome']=='PASS':continue
        failure_path=folder/'batch001_processing_failure.json'
        failed_attempts=[failure_path,folder/(prepared.name+'_processing_failure.json')]
        if any(p.exists() and read(p).get('job_sha256')==sha(ROOT/'config'/('job_'+base+'.json')) for p in failed_attempts):continue
        try:
            if not (prepared/'preparation.json').exists():
                rc=blender('prepare_batch_source.py',ROOT/'config'/('job_'+base+'.json'),folder/(prepared.name+'.log'))
                if rc!=0:raise ValueError('PREPARATION_FAILED; see '+prepared.name+'.log')
            if not (converted/'conversion.json').exists():
                rc=blender('convert_blender.py',prepared/'conversion_job.json',folder/(converted.name+'.log'))
                if rc!=0:raise ValueError('CONVERSION_BLOCKED; see conversion.json and '+converted.name+'.log')
            conversion=read(converted/'conversion.json')
            if conversion['outcome']!='PASS':raise ValueError('CONVERSION_NOT_PASS')
            integrity=inspect(converted/'asset.usdc');write(converted/'integrity.json',integrity)
            if integrity['outcome']!='PASS':raise ValueError('INTEGRITY_FAILED:'+str(integrity['errors']))
            registry=read(ROOT/'registry/assets.json');a=next(x for x in registry['assets'] if x['source']['asset_base_id']==base)
            a.update(last_completed_stage='CONVERTED',dimensions_m=integrity['dimensions_m'],geometry_identity=conversion['geometry_identity'],
                state_id=job['state_id'],usd=dict(path=str((converted/'asset.usdc').relative_to(ROOT)),sha256=sha(converted/'asset.usdc')),
                physics=dict(mode='STATIC_ONLY',mass_kg=None,collision_proxy=None),blockers=['ACTUAL_NATIVE_VISUAL_STATIC_SUPPORT_REPLAY_PENDING','EXTRACTABLE_GENERATOR_RIGHTS_UNCLEARED'])
            for kind in ('conversion','integrity'):
                path=converted/(kind+'.json');a['evidence'][kind]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
            a['processing_job']=dict(path='config/job_'+base+'.json',sha256=sha(ROOT/'config'/('job_'+base+'.json')))
            enrich(a);write(ROOT/'registry/assets.json',registry)
            outcomes.append(dict(asset_id=a['asset_id'],outcome='CONVERTED_INTEGRITY_PASS'))
        except Exception as e:
            failure=dict(outcome='BLOCKED',reason=str(e),source_sha256=job['source']['sha256'],job_sha256=sha(ROOT/'config'/('job_'+base+'.json')))
            # Preserve the first failure; subsequent attempts receive separate receipts.
            if failure_path.exists():failure_path=folder/(prepared.name+'_processing_failure.json')
            write(failure_path,failure)
            registry=read(ROOT/'registry/assets.json');record=next(x for x in registry['assets'] if x['source']['asset_base_id']==base)
            record['processing_failure']=dict(path=str(failure_path.relative_to(ROOT)),sha256=sha(failure_path));record['blockers']=['SOURCE_PROCESSING_RECIPE_REQUIRED',str(e)]
            write(ROOT/'registry/assets.json',registry)
            outcomes.append(dict(asset_id='bk-'+base,outcome='BLOCKED',reason=str(e)))
        print('BATCH_SOURCE_RESULT',base,outcomes[-1]['outcome'],flush=True)
    write(ROOT/'reports/batch_001_processing_latest.json',dict(outcomes=outcomes,scope='New source conversion only; no ready count inferred'))

if __name__=='__main__':main()
