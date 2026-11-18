"""Join explicit inspection decisions to exact native room captures and physics evidence."""
import argparse
from pathlib import Path
import subprocess
import sys
from library import ROOT,read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--decisions',type=Path,required=True);p.add_argument('--html',type=Path,required=True);a=p.parse_args()
    run=a.run.resolve();assert run.is_relative_to(ROOT/'runs')
    verification=read(run/'verification.json');assert verification['outcome']=='PASS'
    capture=run/'native_render';assert read(capture/'process.json')['outcome']=='PASS'
    decisions={(d['level'],d['seed']):d for d in read(a.decisions)['decisions']}
    cases=read(run/'cases.json')['cases'];assert len(cases)==len(decisions)==6;reviews=[]
    for i,(case,pinned) in enumerate(zip(cases,verification['cases'])):
        decision=decisions[(case['level'],case['seed'])];assert decision['outcome']=='PASS' and decision['observations']
        assert sha(case['manifest'])==pinned['manifest_sha256'] and sha(case['scene'])==pinned['scene_sha256']
        folder=Path(case['manifest']).parent;assert read(folder/'native_support.json')['outcome']=='PASS'
        report=read(capture/f'case-{i}/render.json');assert report['manifest_sha256']==sha(case['manifest']) and report['scene_sha256']==sha(case['scene'])
        assert {x['view'] for x in report['images']}=={'overview','floor_foot','bed_surface','pillow_left_detail','chair_seat'}
        images=[]
        for row in report['images']:
            path=capture/f'case-{i}'/row['path'];assert sha(path)==row['sha256']
            images.append(dict(path=str(path),sha256=sha(path),view=row['view']))
        review=dict(outcome='PASS',reviewer='Codex explicit inspection of actual five native PNGs',manifest_sha256=sha(case['manifest']),images=images,
            observations=decision['observations'],scope='Actual fixed-camera room appearance only. Exact physics evidence is separate; no deformable/manipulation or asset-rights promotion.')
        destination=folder/'visual_review.json'
        if destination.exists():assert read(destination)==review
        else:write(destination,review)
        reviews.append(dict(level=case['level'],seed=case['seed'],manifest_sha256=sha(case['manifest']),review_sha256=sha(destination)))
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/report_physics_scenes.py'),'--run',str(run),'--html-output',str(a.html)],check=True)
    write(run/'visual_handoff.json',dict(outcome='PASS',verified_cases=6,reviewed_actual_images=30,cases=reviews,comparison_sha256=sha(a.html),verification_sha256=sha(run/'verification.json'),
        scope='Six exact cases: actual thirty images, initial-static/physics/contact/Replay/dependency proof. No broad dynamic, deformable, rights or perturbation qualification inferred.'))
    print('ACTUAL_SIX_ROOM_VISUAL_HANDOFF_PASS',30)


if __name__=='__main__':main()
