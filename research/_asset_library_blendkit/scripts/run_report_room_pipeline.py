"""Continue existing proposals through real room dynamics, export, capture and packaging."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from library import ROOT,read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--proposals',type=Path,required=True);p.add_argument('--tag',required=True)
    p.add_argument('--after-native-receipt',type=Path);p.add_argument('--public-hotel705',action='store_true');a=p.parse_args()
    work=ROOT/'reports'/(a.tag+'_pipeline');work.mkdir(exist_ok=False);stages=[]
    if a.after_native_receipt:
        write(work/'progress.json',dict(outcome='WAITING',stage='previous_native_session'))
        deadline=time.monotonic()+10800
        while not a.after_native_receipt.exists():
            if time.monotonic()>deadline:raise TimeoutError('PREVIOUS_NATIVE_SESSION_NOT_FINISHED')
            time.sleep(2)
        assert read(a.after_native_receipt)['outcome']=='PASS'
    def run(name,*args,timeout=7200):
        write(work/'progress.json',dict(outcome='RUNNING',stage=name,completed=stages))
        log=work/(name+'.log')
        with log.open('x',encoding='utf-8') as stream:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts'/name),*map(str,args)],cwd=ROOT,
                env={**os.environ,'PYTHONIOENCODING':'utf-8'},stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        stages.append(dict(stage=name,exit_code=result.returncode,log=str(log.relative_to(ROOT)),sha256=sha(log)))
        print('REPORT_ROOM_STAGE',name,result.returncode,flush=True)
        if result.returncode:raise RuntimeError('STAGE_FAILED:'+name)
    try:
        feedback=ROOT/'runs'/(a.tag+'_feedback');settled=ROOT/'runs'/(a.tag+'_settled')
        run('run_physics_guided_scenes.py','--tag',feedback.name,'--proposals',a.proposals)
        assert len(read(feedback/'cases.json')['cases'])==6
        assert all(c['physics_outcome']=='PASS' for c in read(feedback/'cases.json')['cases'])
        run('finalize_physics_scenes.py','--run',feedback,'--tag',settled.name)
        run('verify_physics_scenes.py','--run',settled)
        run('launch_surface_evidence.py','--run',settled,'--kind','render')
        run('report_physics_scenes.py','--run',settled,'--html-output',ROOT/(a.tag+'_comparison.html'))
        extra=['--hotel705-permission'] if a.public_hotel705 else []
        package=ROOT.parent/'_project_delivery/2026-11-19'/(a.tag+'_usd_bundle')
        run('package_room_examples.py','--run',settled,'--output',package,*extra)
        write(work/'result.json',dict(outcome='CAPTURED_PENDING_ACTUAL_VISUAL_REVIEW',stages=stages,
            settled_run=str(settled.relative_to(ROOT)),bundle=str(package),scope='Actual six-case physics and USD closure; image review and publication separate. No soft deformation or asset dynamics promotion.'))
        write(work/'progress.json',dict(outcome='CAPTURED_PENDING_ACTUAL_VISUAL_REVIEW',stage='actual_image_review',completed=stages))
    except Exception as error:
        write(work/'result.json',dict(outcome='BLOCKED',reason=str(error),stages=stages));raise


if __name__=='__main__':main()
