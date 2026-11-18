"""Reuse the proven offline stages for one bounded cohort; stop before visual acceptance."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from library import ROOT,read,write,sha
from process_batch_sources import BLENDER,ENV

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch-id',default='batch_005')
    p.add_argument('--cohort',required=True);p.add_argument('--limit',type=int,default=16)
    p.add_argument('--after-native-receipt',type=Path);a=p.parse_args()
    assert re.fullmatch(r'rigid\d{3}',a.cohort) and all(re.fullmatch(r'batch_\d{3}',b) for b in a.batch_id.split(','))
    assert 1<=a.limit<=16
    work=ROOT/'reports'/(a.cohort+'_pipeline_a000');work.mkdir(exist_ok=False)
    assert not (ROOT/'config'/(a.cohort+'_jobs.json')).exists()
    stages=[]
    def run(label,command,timeout=1800,env=None):
        write(work/'progress.json',dict(stage=label,outcome='RUNNING',completed=stages))
        log=work/(label+'.log')
        with log.open('x',encoding='utf-8') as stream:
            result=subprocess.run(command,cwd=ROOT,env=env or {**os.environ,'PYTHONIOENCODING':'utf-8'},
                                  stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        stages.append(dict(stage=label,exit_code=result.returncode,log=dict(path=str(log.relative_to(ROOT)),sha256=sha(log))))
        print('OFFLINE_COHORT_STAGE',a.cohort,label,result.returncode,flush=True)
        if result.returncode:raise ValueError('STAGE_FAILED:'+label)
    def script(name,*args):return [sys.executable,'-B',str(ROOT/'scripts'/name),*map(str,args)]
    try:
        run('import',script('import_official_batch.py'))
        run('candidate_metadata',script('register_batch_candidates.py'))
        run('probe',[BLENDER,'--background','--factory-startup','--disable-autoexec','--python-exit-code','1',
            '--python',str(ROOT/'scripts/probe_batch_sources.py')],timeout=300,env=ENV)
        run('queue',script('queue_acquired_rigid.py','--batch-id',a.batch_id,'--cohort',a.cohort,'--limit',a.limit))
        jobfile=ROOT/'config'/(a.cohort+'_jobs.json')
        if not jobfile.exists():
            write(work/'result.json',dict(outcome='NO_ELIGIBLE_ACQUIRED_SOURCE_YET',stages=stages));return
        jobs=read(jobfile)['jobs'];ids=[j['base_id'] for j in jobs]
        run('convert',script('process_batch_sources.py','--base-ids',*ids),timeout=7200)
        run('candidate_cases',script('build_batch_cases.py','--pending-only','--cohort',a.cohort,'--base-ids',*ids),timeout=7200)
        cases=ROOT/'config'/(a.cohort+'_cases.json');count=len(read(cases)['cases'])
        if not count:
            write(work/'result.json',dict(outcome='NO_CONVERTED_CANDIDATE_CASE',stages=stages,source_ids=ids));return
        run('merge_room_preparation',script('merge_rigid_cohort.py','--cohorts',a.cohort,'--cohort-out',a.cohort+'_merged'))
        previews=ROOT/'reports'/(a.cohort+'_native_previews_a000')
        support=ROOT/'runs'/(a.cohort+'_native_support_a000')
        render=ROOT/'runs'/(a.cohort+'_scene_render_a000')
        if a.after_native_receipt:
            receipt=a.after_native_receipt.resolve();assert receipt.is_relative_to(ROOT/'runs')
            write(work/'progress.json',dict(stage='wait_for_previous_native_session',outcome='WAITING',completed=stages))
            deadline=time.monotonic()+7200
            while not receipt.exists():
                if time.monotonic()>deadline:raise TimeoutError('PREVIOUS_NATIVE_SESSION_NOT_COMPLETE')
                time.sleep(2)
            assert read(receipt)['outcome']=='PASS'
        run('native_asset_capture',script('run_asset_preview_batch.py','--jobs',ROOT/'config'/(a.cohort+'_preview_jobs.json'),
            '--output',previews,'--timeout','1200'))
        run('native_support',script('dispatch_core_batch.py','--kind','support','--cases',cases,
            '--shared-config',ROOT/'config'/(a.cohort+'_merged_shared')/'deployment.json','--output',support))
        run('native_room_capture',script('dispatch_core_batch.py','--kind','render','--cases',cases,'--output',render))
        write(work/'result.json',dict(outcome='PENDING_ACTUAL_VISUAL_REVIEW',stages=stages,source_ids=ids,
            candidate_cases=count,cases=str(cases.relative_to(ROOT)),previews=str(previews.relative_to(ROOT)),
            support=str(support.relative_to(ROOT)),room_render=str(render.relative_to(ROOT)),
            worker_sha256=sha(__file__),scope='Real sources only. All actual PNGs require explicit inspection before local acceptance. No rights or dynamics promotion.'))
        write(work/'progress.json',dict(stage='actual_visual_review_required',outcome='PENDING_ACTUAL_VISUAL_REVIEW',completed=stages))
    except Exception as error:
        write(work/'result.json',dict(outcome='BLOCKED',reason=str(error),stages=stages,
            scope='Preserve all attempts; do not retry automatically or infer acceptance'))
        raise

if __name__=='__main__':main()
