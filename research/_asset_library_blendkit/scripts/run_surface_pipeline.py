"""One process for future scene generation, native support and all ten fixed views."""
import argparse,re,subprocess,sys
from pathlib import Path
from library import ROOT,read,write,sha

def corrected_camera_batch(batch):
    import copy
    batch=copy.deepcopy(batch)
    additions=dict(pillow_left_detail=dict(eye=[1.05,-4.545,1.65],target=[2.18,-4.545,.94],focal=25),
        pillow_right_detail=dict(eye=[1.05,-5.445,1.65],target=[2.18,-5.445,.94],focal=25),
        single_bed_clear=dict(eye=[.15,-4.12,1.55],target=[1.25,-3.2,.5],focal=22),
        between_beds=dict(eye=[-.1,-3.8,1.5],target=[1.3,-3.75,.15],focal=26),
        floor_window=dict(eye=[.45,-6.2,1.8],target=[1.8,-7,.1],focal=22))
    for c in batch['cases']:
        c['cameras']={k:v for k,v in c['cameras'].items() if k not in {'pillows','single_bed'}};c['cameras'].update(additions)
    return batch

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--seeds',type=int,nargs=2,default=[706,707]);a=p.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_]{1,80}',a.tag):raise ValueError('SIMPLE_UNIQUE_TAG_REQUIRED')
    if len(set(a.seeds))!=2:raise ValueError('TWO_DISTINCT_SEEDS_REQUIRED')
    run=ROOT/'runs'/a.tag;cfg=ROOT/'config'/a.tag
    if run.exists() or cfg.exists():raise ValueError('NEW_TAG_REQUIRED_PRESERVE_EXISTING_EVIDENCE')
    def execute(script,*args):subprocess.run([sys.executable,'-B',str(ROOT/'scripts'/script),*map(str,args)],cwd=ROOT,check=True)
    execute('generate_surface_scenes.py','--tag',a.tag,'--seeds',*a.seeds)
    snap=cfg/'producer_sources';snap.mkdir();pins=[]
    for name in ['generate_surface_scenes.py','expanded_surfaces.py','surface_geometry.py']:
        f=snap/name;f.write_bytes((ROOT/'scripts'/name).read_bytes());pins.append(dict(path=str(f.relative_to(ROOT)),sha256=sha(f)))
    for c in read(run/'cases.json')['cases']:
        assert read(Path(c['manifest']).parent/'contact_samples.json')['generator_sha256']==sha(snap/'generate_surface_scenes.py')
    write(cfg/'producer_sources.json',dict(outcome='EXACT_GENERATING_SOURCE_BYTES_PINNED',files=pins))
    batch=corrected_camera_batch(read(run/'render_batch.json'))
    write(run/'render_final_batch.json',batch)
    execute('launch_surface_evidence.py','--run',run,'--kind','support')
    execute('launch_surface_evidence.py','--run',run,'--kind','render','--render-batch',run/'render_final_batch.json')
    execute('report_surface_scenes.py','--run',run)
    write(run/'capture_pipeline.json',dict(outcome='CAPTURED_PENDING_ACTUAL_VISUAL_REVIEW',cases=6,images=60,
        next_step='Inspect actual PNGs, supply explicit per-case decisions to finalize_surface_scenes.py, then run evidence verification. No automatic visual or rights acceptance.'))
    print('SCENE_PIPELINE_CAPTURED',run,'ACTUAL_VISUAL_REVIEW_PENDING')

if __name__=='__main__':main()
