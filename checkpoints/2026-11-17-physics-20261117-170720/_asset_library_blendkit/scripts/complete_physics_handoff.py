"""Guarded local handoff of reviewed exact-case results; grants no asset rights."""
from library import ROOT,read,write,sha
from pathlib import Path
import argparse,shutil,subprocess

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();run=a.run.resolve()
    verification=read(run/'verification.json');assert verification['outcome']=='PASS'
    assert read(run/'sensitivity.json')['outcome']=='PASS'
    assert read(run/'native_render_a001/process.json')['outcome']=='PASS'
    assert read(run/'comparison_ui_check.json')['outcome']=='PASS'
    assert read(run/'comparison_ui_check.json')['page_sha256']==sha(ROOT/'physics_comparison.html')
    cases=read(run/'cases.json')['cases'];assert len(cases)==6
    for c,v in zip(cases,verification['cases']):
        assert sha(c['manifest'])==v['manifest_sha256'] and sha(c['scene'])==v['scene_sha256']
        folder=Path(c['manifest']).parent;review=read(folder/'visual_review.json');assert review['outcome']=='PASS' and len(review['images'])==5
        for im in review['images']:assert sha(im['path'])==im['sha256']
        assert read(folder/'native_support.json')['outcome']=='PASS'
    status=subprocess.run(['git','-C',str(ROOT.parent/'common_core'),'-c','safe.directory=C:/hotel_room/common_core','diff','--stat'],capture_output=True,text=True)
    assert status.returncode==0 and not status.stdout.strip(),status.stdout+status.stderr
    backup=ROOT/('comparison_before_'+run.name+'.html')
    if not backup.exists():shutil.copy2(ROOT/'comparison.html',backup)
    shutil.copy2(ROOT/'physics_comparison.html',ROOT/'comparison.html')
    write(ROOT/'registry/latest_physics_run.json',dict(run=str(run),cases=str(run/'cases.json'),comparison='comparison.html',verification_sha256=sha(run/'verification.json'),scope='Exact local rigid-surrogate scene qualification only; all library asset physics/rights gates retained'))
    write(run/'handoff.json',dict(outcome='PASS',reviewed_images=30,verified_cases=6,comparison_sha256=sha(ROOT/'comparison.html'),protected=verification['protected'],formal_core_git_diff='',scope='Local handoff; no push/publication, no blanket dynamic/flexible/manipulation or public rights qualification'))
    print('PHYSICS_LOCAL_HANDOFF_PASS',run)

if __name__=='__main__':main()
