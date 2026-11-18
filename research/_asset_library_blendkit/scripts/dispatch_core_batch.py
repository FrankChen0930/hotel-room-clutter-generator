"""Dispatch only new candidate manifests through the established Core native workers."""
import argparse
from pathlib import Path
import runpy
import sys
from library import ROOT,read,write
import usd_sdk

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['support','render'],required=True)
    p.add_argument('--cases',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--views',nargs='+');p.add_argument('--shared-config',type=Path);a=p.parse_args()
    usd_sdk.load();core=ROOT.parent/'common_core';sys.path.insert(0,str(core));sys.path.insert(0,str(core/'tools'))
    import common_core.paths
    common_core.paths.RUN_ROOT=ROOT/'runs'
    cases=read(a.cases)['cases'];rows=[]
    ref=ROOT.parent/'_common_core_runs/quality_experiments/scene_quality_v02_20261114T153126Z'
    cameras={x['view']:x['camera'] for c in read(ref/'comparison_index.json')['cases'] if c['version']=='v4_bed' for x in c['images']}
    for case in cases:
        if a.kind=='support':
            config=a.shared_config.resolve() if a.shared_config else Path(case['config'])
            if a.shared_config:
                assert config.is_relative_to(ROOT/'config')
                merge=read(config.parent/'merge_receipt.json')
                assert merge['outcome']=='PASS' and case['asset_id'] in merge['new_asset_ids']
                from library import sha
                assert any(x['sha256']==sha(case['config']) for x in merge['inputs'])
            rows.append(dict(room='hotel705',manifest=case['manifest'],config=str(config)))
        else:
            manifest=read(case['manifest']);obj=next(x for x in manifest['objects'] if x['asset_id']==case['asset_id']);sid=obj['effective']['support_id']
            view='floor_bedside' if sid=='floor_bedside' else 'floor_foot' if sid.startswith('floor_') else 'entry_bench' if sid=='bench' else 'desk' if sid=='desk' else 'minibar' if sid=='minibar' else 'bed'
            rows.append(dict(manifest=case['manifest'],cameras={v:cameras[v] for v in (a.views or ('overview',view))}))
    batch=a.output.with_suffix('.batch.json');write(batch,dict(cases=rows,source_cases=str(a.cases.resolve())))
    worker=ref/'scripts/launch_support_experiment.py' if a.kind=='support' else core/'tools/launch_render.py'
    sys.argv=[str(worker),'--batch',str(batch),'--output',str(a.output.resolve()),'--timeout','900' if a.kind=='render' else '600']
    runpy.run_path(str(worker),run_name='__main__')
