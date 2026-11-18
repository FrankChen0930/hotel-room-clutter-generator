"""Pin the manually inspected five-source comparison and actual native evidence."""
from collections import Counter
import argparse
from pathlib import Path
from library import ROOT,read,write,sha,artifact_ok,gate_errors

def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=ROOT/'runs/local_pool_batch001_a002');p.add_argument('--review',type=Path);args=p.parse_args()
    run=args.run.resolve();assert run.is_relative_to(ROOT/'runs');case=read(run/'case_index.json');attempt=Path(case['manifest']).parent;manifest=read(case['manifest'])
    for p in [attempt/'static.json',attempt/'integrity.json',attempt/'replay.json',run/'native_support/process.json',run/'native_support/result.json',run/'native_support/case-0.json',run/'native_render/process.json']:assert read(p)['outcome']=='PASS',str(p)
    native=read(run/'native_render/case-0/render.json');assert native['manifest_sha256']==sha(case['manifest']) and native['scene_sha256']==sha(case['scene'])
    reference=ROOT.parent/'_common_core_runs/quality_experiments/scene_quality_v02_20261114T153126Z'
    cameras={im['view']:im['camera'] for c in read(reference/'comparison_index.json')['cases'] if c['version']=='v4_bed' for im in c['images']}
    images=[]
    for im in native['images']:
        path=run/'native_render/case-0'/im['path'];assert sha(path)==im['sha256'] and im['camera']==cameras[im['view']];images.append(ref(path))
    records={a['asset_id']:a for a in read(ROOT/'registry/assets.json')['assets']}
    support=read(run/'native_support/case-0.json');assert support['manifest_sha256']==sha(case['manifest'])
    used=[]
    for obj in manifest['objects']:
        if obj['asset_id'] not in case['asset_ids']:continue
        a=records[obj['asset_id']];assert not gate_errors(a,scope='local')
        checks=[x for x in support['checks'] if x['instance_id']==obj['instance_id']];assert len(checks)==9 and all(x['passed'] for x in checks)
        used.append(dict(asset_id=a['asset_id'],appearance_family=a['appearance_family'],geometry_family=a['geometry_family'],
            support=obj['effective']['support_id'],state_id=obj['effective']['state_id'],source_url=a['source']['url'],license=a['rights']['license'],native_queries=len(checks)))
    groups=read(reference/'config/appearance_policy.json')['rooms']['hotel705']['scenarios']['STAYOVER']['groups']
    families={records[o['asset_id']]['appearance_family'] if o['asset_id'] in records else groups.get(o['asset_id']+'/'+o['effective']['state_id'],groups.get(o['asset_id'],o['asset_id']+'/'+o['effective']['state_id'])) for o in manifest['objects']}
    observations=['Actual overview, floor_foot, floor_bedside and entry_bench PNGs inspected.',
        'Suitcase near chair, grey backpack and single shoe beside bed, corduroy backpack and folded trousers on bench; no new objects concentrated on desk.',
        'Natural room-scale fabrics/leather and canvas details preserved; conservative support proxies do not show in image.',
        'Bench is relatively full; this candidate demonstrates distribution, not a universal density recommendation.',
        'Main bed duvet surface remains unchanged and unsolved; no manual object repositioning or image retouching.']
    if args.review:
        review=read(args.review);assert review['outcome']=='PASS' and review['reviewer'];observations=review['observations']
    else:assert run==ROOT/'runs/local_pool_batch001_a002','A different scene requires its explicit actual visual review'
    write(run/'scene_visual_review.json',dict(outcome='PASS',reviewer='Codex actual four-view Isaac PNG inspection',images=images,observations=observations))
    write(run/'asset_usage.json',dict(assets=used,generated_objects=len(manifest['objects']),support_distribution=dict(Counter(o['effective']['support_id'] for o in manifest['objects']))))
    write(run/'scene_quality_summary.json',dict(outcome='ACCEPT_LOCAL_PREVIEW',room='hotel705',scenario='STAYOVER',level='high',seed=706,
        generated_instances=len(manifest['objects']),generated_unique_asset_ids=len({o['asset_id'] for o in manifest['objects']}),generated_appearance_families=len(families),
        new_independent_blendkit_sources_used=len(used),new_appearance_families=len({x['appearance_family'] for x in used}),
        reference_v02_instances=25,reference_v02_unique_asset_ids=22,reference_v02_appearance_families=18,
        placement='Seeded Common Core sampler; independent documented replacement policy; no hand-edited poses',observations=observations,
        limits=['CONTROLLED_LOCAL_ONLY','STATIC_ONLY','No rights clearance for extractable generator/public sharing']))
    write(run/'local_qualification.json',dict(outcome='PASS',manifest=ref(Path(case['manifest'])),scene=ref(Path(case['scene'])),new_source_count=len(used),native_queries=sum(x['native_queries'] for x in used),
        static='PASS',integrity='PASS',replay='PASS',native_support='PASS',actual_visual_review='PASS',generator_ready=False,public_starter=False))
    write(ROOT/'registry/latest_local_scene.json',case)
    print('ACTUAL_POOL_SCENE_QUALIFIED',len(used),'sources;',len(families),'appearance families')

if __name__=='__main__':main()
