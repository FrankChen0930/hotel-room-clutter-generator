"""Join explicit image reviews and per-scene evidence; keep source asset rights unchanged."""
import argparse
from pathlib import Path
from collections import Counter
from library import ROOT,read,write,sha
from report_surface_scenes import collect
from generate_surface_scenes import eligible

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--decisions',type=Path,required=True);a=p.parse_args()
    run=a.run.resolve();cases=read(run/'cases.json')['cases'];decisions={(d['level'],d['seed']):d for d in read(a.decisions)['decisions']}
    registry=read(ROOT/'registry/assets.json');records={r['asset_id']:r for r in registry['assets']};reviews=[];pairs={}
    assert read(run/'native_support/result.json')['outcome']=='PASS' and read(run/'reproducibility.json')['outcome']=='PASS'
    for i,case in enumerate(cases):
        decision=decisions[(case['level'],case['seed'])];assert decision['outcome']=='PASS' and decision['observations']
        manifest=read(case['manifest']);attempt=Path(case['manifest']).parent
        for kind in ['static','integrity','replay']:assert read(attempt/(kind+'.json'))['outcome']=='PASS'
        support=read(run/'native_support'/('case-'+str(i)+'.json'));assert support['outcome']=='PASS' and all(c['passed'] for c in support['checks'])
        assert support['manifest_sha256']==sha(case['manifest'])
        images=collect(run,i);review=dict(outcome='PASS',reviewer='Codex actual native PNG inspection of all ten selected views',manifest_sha256=sha(case['manifest']),
            images=list(images.values()),observations=decision['observations'],scope='Static room appearance; no dynamic, flexible-object or manipulation qualification')
        write(attempt/'scene_visual_review.json',review)
        qualification=dict(outcome='PASS_CONTROLLED_LOCAL_MULTI_SURFACE',static='PASS',integrity='PASS',replay='PASS',native_triangle_support='PASS',visual='PASS',
            native_queries=len(support['checks']),added_objects=len(manifest['objects']),unique_assets=len({o['asset_id'] for o in manifest['objects']}),
            support_distribution=dict(Counter(o['effective']['support_id'] for o in manifest['objects'])),generation_ready=False,public_starter=False,
            native_scope='Unchanged source mesh, exact triangle approximation in unsaved session; original approximation/dynamics not qualified',
            manifest=dict(path=str(Path(case['manifest']).relative_to(ROOT)),sha256=sha(case['manifest'])),visual_review=dict(path=str((attempt/'scene_visual_review.json').relative_to(ROOT)),sha256=sha(attempt/'scene_visual_review.json')))
        write(attempt/'scene_qualification.json',qualification);reviews.append(dict(level=case['level'],seed=case['seed'],**qualification))
        for obj in manifest['objects']:
            key=(obj['asset_id'],obj['effective']['state_id'],obj['effective']['support_id'])
            pairs.setdefault(key,[]).append(dict(manifest=qualification['manifest'],qualification=dict(path=str((attempt/'scene_qualification.json').relative_to(ROOT)),sha256=sha(attempt/'scene_qualification.json'))))
    specs=read(Path(cases[0]['config']).parent/'surfaces.json')['surfaces'];candidate=[]
    for record in records.values():
        if record.get('local_qualification',{}).get('outcome')!='PASS':continue
        regions=[s['support_id'] for s in specs if eligible(record,s['support_id'],[record['category']])]
        candidate.append(dict(asset_id=record['asset_id'],state_id=record['state_id'],usd_sha256=record['usd']['sha256'],eligible_to_sample=regions,
            scope='Semantic/dimension pre-screen only; each generated pose still needs dense geometry, native and visual validation'))
    observed=[dict(asset_id=aid,state_id=state,support_id=sid,usd_sha256=records[aid]['usd']['sha256'],evidence=proof) for (aid,state,sid),proof in pairs.items()]
    policy=run/'placement_region_qualifications.json';write(policy,dict(outcome='LOCAL_OBSERVED_PAIRS_AND_CANDIDATE_REGIONS',candidates=candidate,observed_native_visual_pairs=observed,
        surface_config=dict(path=str((Path(cases[0]['config']).parent/'surfaces.json').relative_to(ROOT)),sha256=sha(Path(cases[0]['config']).parent/'surfaces.json')),
        limits=['STATIC_ONLY','No geometry/material/source edits','No blanket qualification of unobserved asset/surface pairs','No extractable generator/public rights granted']))
    reference=dict(path=str(policy.relative_to(ROOT)),sha256=sha(policy))
    for record in registry['assets']:
        regions=sorted({row['support_id'] for row in observed if row['asset_id']==record['asset_id']})
        if regions:record['scene_surface_qualifications']=dict(regions=regions,evidence=reference,scope='CONTROLLED_LOCAL_STATIC_SOURCE_TRIANGLES_ONLY')
    write(ROOT/'registry/assets.json',registry);write(run/'visual_reviews.json',dict(outcome='PASS',cases=reviews))
    write(ROOT/'registry/latest_surface_run.json',dict(run=str(run.relative_to(ROOT)),cases=dict(path=str((run/'cases.json').relative_to(ROOT)),sha256=sha(run/'cases.json')),
        placement_policy=reference,scope='Six controlled local degree/seed scenes; formal baseline and original latest-local-scene pointer retained'))
    print('MULTI_SURFACE_SCENES_QUALIFIED',len(reviews),'OBSERVED_ASSET_SURFACE_PAIRS',len(observed))

if __name__=='__main__':main()
