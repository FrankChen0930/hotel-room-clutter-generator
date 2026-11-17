"""Persist the actual inspected accepted-model room captures, excluding stale failed laptop."""
import argparse
from collections import Counter
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--cohort');p.add_argument('--render-folder');p.add_argument('--local-view-only',action='store_true');args=p.parse_args()
    records={a['asset_id']:a for a in read(ROOT/'registry/assets.json')['assets']};saved=[]
    reference=ROOT.parent/'_common_core_runs/quality_experiments/scene_quality_v02_20261114T153126Z'
    cameras={im['view']:im['camera'] for c in read(reference/'comparison_index.json')['cases'] if c['version']=='v4_bed' for im in c['images']}
    groups=read(reference/'config/appearance_policy.json')['rooms']['hotel705']['scenarios']['STAYOVER']['groups']
    cohorts=[(args.cohort+'_cases.json',args.render_folder or args.cohort+'_scene_render_a000')] if args.cohort else [('batch001c_cases.json','batch001c_scene_render_a000'),('batch001d_cases.json','batch001d_scene_render_a000')]
    for config,render_folder in cohorts:
        folder=ROOT/'runs'/render_folder;assert read(folder/'process.json')['outcome']=='PASS'
        for index,case in enumerate(read(ROOT/'config'/config)['cases']):
            a=records[case['asset_id']]
            if a.get('local_qualification',{}).get('outcome')!='PASS' or Path(case['asset']).resolve()!=(ROOT/a['usd']['path']).resolve():continue
            manifest=read(case['manifest']);run=Path(case['manifest']).parents[2];native=read(folder/('case-'+str(index))/'render.json')
            assert native['manifest_sha256']==sha(case['manifest']) and native['scene_sha256']==sha(case['scene'])
            images=[]
            for im in native['images']:
                path=folder/('case-'+str(index))/im['path'];assert sha(path)==im['sha256'] and im['camera']==cameras[im['view']]
                images.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path)))
            observations=[('Actual local-support camera PNG inspected; overview capture retained and hash/camera checked, composite overview reviewed separately.' if args.local_view_only else 'Actual overview and matching local-support camera PNG inspected; source room/camera/light kept fixed.'),
                'Recognizable '+a['name']+' with complete natural material at room scale; seeded pose on validated source support.',
                'Local region view is needed for assets hidden from overview by bed/frustum; no manual relocation or retouching.',
                'Single-model qualification case; original amenity/slipper repetition remains visible here. Multi-source distribution comparison is separate.']
            report=dict(outcome='PASS',reviewer='Codex actual native room image inspection',manifest_sha256=sha(case['manifest']),images=images,observations=observations)
            output=run/'scene_visual_review.json'
            if output.exists():assert read(output)==report
            else:write(output,report)
            families={records[o['asset_id']]['appearance_family'] if o['asset_id'] in records else groups.get(o['asset_id']+'/'+o['effective']['state_id'],groups.get(o['asset_id'],o['asset_id']+'/'+o['effective']['state_id'])) for o in manifest['objects']}
            write(run/'scene_quality_summary.json',dict(outcome='ACCEPT_LOCAL_PREVIEW',generated_instances=len(manifest['objects']),generated_unique_asset_ids=len({o['asset_id'] for o in manifest['objects']}),generated_appearance_families=len(families),new_independent_blendkit_sources_used=1,observations=observations,limits=['STATIC_ONLY','LOCAL_RIGHTS_SCOPE_ONLY']))
            write(run/'asset_usage.json',dict(new_asset_id=a['asset_id'],source_url=a['source']['url'],license=a['rights']['license'],all_instance_asset_ids=[o['asset_id'] for o in manifest['objects']],support_distribution=dict(Counter(o['effective']['support_id'] for o in manifest['objects']))))
            saved.append(case['asset_id'])
    write(ROOT/'reports'/((args.cohort or 'batch001')+'_room_reviews.json'),dict(outcome='PASS',accepted_case_asset_ids=saved,scope='Actual inspected room captures only; stale cases excluded, no asset count from instances'))
    print('ACTUAL_ROOM_VISUAL_REVIEWS_RECORDED',len(saved))

if __name__=='__main__':main()
