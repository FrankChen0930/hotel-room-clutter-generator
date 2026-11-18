"""Prepare bounded offline recipes from official intake; never auto-accept a model."""
import argparse
import re
from library import ROOT,read,write
from source_variants import candidate_variant_key
from batch_selection import semantic_rejection

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--batch-id',required=True)
    p.add_argument('--cohort',required=True)
    p.add_argument('--limit',type=int,default=16)
    args=p.parse_args()
    batch_ids=set(args.batch_id.split(','))
    assert batch_ids and all(re.fullmatch(r'batch_\d{3}',b) for b in batch_ids)
    assert re.fullmatch(r'rigid\d{3}',args.cohort) and 1<=args.limit<=16
    output=ROOT/'config'/(args.cohort+'_jobs.json')
    if output.exists():raise ValueError('COHORT_EXISTS_PRESERVE_PRIOR_EVIDENCE')
    master=read(ROOT/'config/batch_001_processing_jobs.json')
    known={j['base_id'] for j in master['jobs']};jobs=[];deferred=[]
    order={'electronics':0,'personal':1,'toiletry':2,'food':3,'paper':4,'luggage':5}
    def priority(a):
        modern=a['category']=='electronics' and any(word in a['name'].lower() for word in ('iphone','smartphone','ipad','laptop','macbook','power bank'))
        return order.get(a['category'],99),0 if modern else 1,a['asset_id']
    records=sorted(read(ROOT/'registry/assets.json')['assets'],key=priority)
    representative={}
    for item in records:
        probe_path=ROOT/'reports'/(item['source']['asset_base_id']+'_batch001_probe.json')
        if item.get('local_qualification',{}).get('outcome')=='PASS' and probe_path.exists():
            key=candidate_variant_key(item,read(probe_path))
            if key:representative.setdefault(key,item.get('variant_of') or item['asset_id'])
    for a in records:
        base=a['source']['asset_base_id']
        if a.get('batch_id') not in batch_ids or base in known or a['status']=='REJECTED' or not a['source'].get('original_file'):continue
        reason=None;name=a['name'].lower()
        if a['category'] not in order:reason='SOFT_OR_LOWER_PRIORITY_CATEGORY_DEFERRED'
        elif semantic_rejection(name,a['category']):reason='HOTEL_SEMANTIC_RECHECK_FAILED'
        if re.search(r'\b(?:cables?|cords?|wired|bags?|pouches|wallets?|passports?|tubes?|packets?|wrappers?)\b',name):
            reason='FLEXIBLE_OR_MIXED_FORM_REQUIRES_EXPLICIT_SELECTION'
        if re.search(r'\b(?:kit|set|collection|pile|pack)\b',name):
            reason='MULTI_PROP_SET_REQUIRES_EXPLICIT_COMPONENT_RECIPE'
        path=ROOT/'reports'/(base+'_batch001_probe.json')
        probe=read(path) if path.exists() else None
        if probe is None:reason='OFFLINE_SOURCE_PROBE_REQUIRED'
        elif probe['libraries']:reason='EXTERNAL_LIBRARY_RECIPE_REQUIRED'
        elif any(o['type'] in ('CURVE','CURVES') for o in probe['objects']):reason='CURVE_COMPONENT_REQUIRES_EXPLICIT_RECIPE'
        elif any(o['instance_type']!='NONE' and not o['hidden'] and not o['hide_render'] for o in probe['objects']):
            reason='VISIBLE_SOURCE_INSTANCES_REQUIRE_EXPLICIT_REALIZATION'
        meshes=[] if probe is None else [o['name'] for o in probe['objects'] if o['type']=='MESH' and not o['hidden'] and not o['hide_render']]
        if any(re.search(r'(^|[\s_.])(cable|wire|cord)([\s_.0-9]|$)',mesh.lower()) for mesh in meshes):
            reason='MESH_CABLE_COMPONENT_DEFERRED'
        if not meshes:reason=reason or 'NO_VISIBLE_SOURCE_MESH'
        key=candidate_variant_key(a,probe) if probe is not None else None
        if key and key in representative:
            deferred.append(dict(asset_id=a['asset_id'],reason='LIKELY_COLORWAY_DEFERRED_TO_AVOID_DUPLICATE_WORK',reference=representative[key]));continue
        if reason:
            deferred.append(dict(asset_id=a['asset_id'],reason=reason));continue
        if len(jobs)>=args.limit:continue
        job=dict(base_id=base,source=a['source']['original_file'],meshes=meshes,
            prepare_dir=f'artifacts/{base}/prepare_{args.cohort}_a000',
            conversion_dir=f'artifacts/{base}/convert_{args.cohort}_a000',
            dimension_bounds_m=dict(min=[.003,.003,.001],max=[.65,.65,.65]),
            allow_base_color_bake=True,allow_multi_material_bake=True,allow_simple_surface_recipes=True,
            allow_bump_only_normal_bake=True,bump_bake_resolution=1024,max_texture_dimension=2048,
            source_root_rotation_deg=[0,0,0],state_id='source_fixed_form',supports=['bench'],
            replace_request_ids=['quality/s0_towel/1'],tag=args.cohort+'_'+base[:8],
            selection_note='Initial complete visible-mesh candidate. Sets, geometry families, hotel relevance and material fidelity require actual native review.')
        master['jobs'].append(job);jobs.append(job);known.add(base)
        if key:representative[key]=a['asset_id']
        write(ROOT/'config'/('job_'+base+'.json'),job)
    if not jobs:
        write(ROOT/'reports'/(args.cohort+'_queue_deferred.json'),dict(deferred=deferred,scope='No cohort reserved; resume after source/probe prerequisites arrive'))
        print('NO_NEW_ELIGIBLE_RECIPES_YET');return
    write(ROOT/'config/batch_001_processing_jobs.json',master)
    write(output,dict(jobs=jobs,deferred=deferred,source_batches=sorted(batch_ids),
        scope='Offline queue only; source acquisition, technical acceptance, rights and dynamics remain independent gates'))
    print('NEW_ACQUIRED_RIGID_RECIPES',len(jobs),'DEFERRED',len(deferred))

if __name__=='__main__':main()
