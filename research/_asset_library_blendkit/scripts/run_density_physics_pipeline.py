"""One command: independent density proposals, bounded physics repair, settled export/capture."""
import argparse,subprocess,sys
from pathlib import Path
from library import ROOT,read,write

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--seeds',type=int,nargs='+',default=[706,707]);p.add_argument('--catalog-config',type=Path);p.add_argument('--hotel-native-only',action='store_true');p.add_argument('--portable-source-inventory',type=Path);a=p.parse_args()
    if a.portable_source_inventory:assert a.hotel_native_only
    def execute(name,*args):subprocess.run([sys.executable,'-B',str(ROOT/'scripts'/name),*map(str,args)],cwd=ROOT,check=True)
    proposals=a.tag+'_proposals';feedback=a.tag+'_feedback';settled=a.tag+'_settled'
    extra=['--catalog-config',a.catalog_config] if a.catalog_config else []
    if a.hotel_native_only:extra.append('--hotel-native-only')
    execute('generate_dense_scenes.py','--tag',proposals,'--seeds',*a.seeds,*extra)
    execute('run_physics_guided_scenes.py','--tag',feedback,'--proposals',ROOT/'runs'/proposals)
    cases=read(ROOT/'runs'/feedback/'cases.json')['cases']
    if not all(c['physics_outcome']=='PASS' for c in cases):raise RuntimeError('Unresolved physics cases preserved; no accepted export produced')
    execute('finalize_physics_scenes.py','--run',ROOT/'runs'/feedback,'--tag',settled)
    verify_extra=['--portable-source-inventory',a.portable_source_inventory] if a.portable_source_inventory else []
    execute('verify_physics_scenes.py','--run',ROOT/'runs'/settled,*verify_extra)
    execute('launch_surface_evidence.py','--run',ROOT/'runs'/settled,'--kind','render')
    execute('report_physics_scenes.py','--run',ROOT/'runs'/settled,'--html-output',ROOT/(a.tag+'_comparison.html'))
    if not a.portable_source_inventory:execute('verify_protected.py')
    write(ROOT/'runs'/settled/'pipeline.json',dict(outcome='CAPTURED_PENDING_ACTUAL_VISUAL_REVIEW',next_step='Inspect actual native PNGs; do not auto-promote asset rights/dynamic/flexible qualification'))
    print('PHYSICS_DENSITY_PIPELINE_CAPTURED',ROOT/'runs'/settled)

if __name__=='__main__':main()
