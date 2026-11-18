"""Compose the accepted local pool using the existing deterministic Core placer."""
import argparse
from integrate_real_backpack import *
from library import gate_errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--seed',type=int,default=706);p.add_argument('--max-new',type=int,default=5);p.add_argument('--catalog-only',action='store_true');args=p.parse_args();tag=args.tag
    registry=read(ROOT/'registry/assets.json')['assets']
    assets=[];seen_geometry=set()
    for a in registry:
        if a.get('local_qualification',{}).get('outcome')!='PASS' or a.get('variant_of'):continue
        if a['geometry_identity'] in seen_geometry:continue
        assets.append(a);seen_geometry.add(a['geometry_identity'])
    assert len(assets)>=2
    for a in assets:assert not gate_errors(a,scope='local')
    from hotel_metadata import choose_local_subset
    selected_assets=choose_local_subset(assets,args.seed,args.max_new)
    selected_ids={a['asset_id'] for a in selected_assets}
    reserve_bedside=any(a['category']=='footwear' and a['dimensions_m'][0]*a['dimensions_m'][1]>.06 for a in selected_assets)
    first=read(ROOT/'registry/latest_local_scene.json');source_config=Path(first['config']).parent
    cfgdir=ROOT/('config/local_pool_'+tag);cfgdir.mkdir(exist_ok=False)
    cfg=read(source_config/'deployment.json');profile=read(source_config/'profile.json');policy=read(source_config/'policy.json')
    catalog=read(source_config/'catalog.json');lock=read(source_config/'source_lock.json')
    requests=[];cats=set();states={}
    for a in assets:
        manifest_path=ROOT/a['local_qualification']['scene_manifest']['path'];manifest=read(manifest_path)
        case=read(manifest_path.parents[2]/'case_index.json');other=Path(case['config']).parent
        entry=copy.deepcopy(next(e for e in read(other/'catalog.json')['entries'] if e['asset_id']==a['asset_id']))
        if not any(e['asset_id']==a['asset_id'] for e in catalog['entries']):catalog['entries'].append(entry)
        for dep in read(other/'source_lock.json')['assets']:
            if dep not in lock['assets']:lock['assets'].append(dep)
        request=copy.deepcopy(next(r for r in manifest['requests'] if r['asset_id']==a['asset_id']))
        # Region eligibility only: every actual pose remains sampled by Core.
        if a['category']=='clothing':request['allowed_support_ids']=['bench']
        elif a['category']=='footwear':request['allowed_support_ids']=['floor_bedside']
        elif a['category']=='bag' and reserve_bedside:request['allowed_support_ids']=['bench','floor_luggage']
        elif a['category']=='electronics' and a['dimensions_m'][0]*a['dimensions_m'][1]<=.06:request['allowed_support_ids']=['desk']
        elif a['category'] in {'paper','electronics'}:request['allowed_support_ids']=['bench','desk']
        elif a['category']=='personal':request['allowed_support_ids']=['desk','bench','minibar']
        elif a['category']=='toiletry':request['allowed_support_ids']=['bench','minibar']
        elif a['category']=='towel':request['allowed_support_ids']=['floor_luggage','bench']
        elif a['state_id']=='upright_scan':request['allowed_support_ids']=['bench','floor_luggage']
        else:request['allowed_support_ids']=['floor_luggage','floor_bedside']
        if a['asset_id'] in selected_ids:requests.append(request)
        cats.add(a['category']);states.setdefault(a['category'],set()).add(a['state_id'])
    # Larger footprints first; this changes no final pose manually.
    requests.sort(key=lambda r: -next(a['dimensions_m'][0]*a['dimensions_m'][1] for a in assets if a['asset_id']==r['asset_id']))
    for scope in (policy['scenarios']['STAYOVER'],policy['levels']['high']):scope['eligible_categories']=sorted(set(scope['eligible_categories'])|cats)
    for cat,values in states.items():
        prior=policy['levels']['high'].get('allowed_states',{}).get(cat)
        if prior is None:prior=[s['state_id'] for e in catalog['entries'] if e['category']==cat for s in e['states']]
        policy['levels']['high'].setdefault('allowed_states',{})[cat]=sorted(set(prior)|values)
    profile['profile_version']='local-pool-'+tag;catalog['version']='local-pool-'+tag
    for name,value in [('deployment.json',cfg),('profile.json',profile),('policy.json',policy),('catalog.json',catalog),('source_lock.json',lock)]:write(cfgdir/name,value)
    inputs=load_inputs(cfgdir/'deployment.json','hotel705')
    if args.catalog_only:
        write(ROOT/'registry/local_catalog_latest.json',dict(outcome='CONTROLLED_LOCAL_CANDIDATE_CATALOG_LOAD_PASS',
            deployment=str(cfgdir/'deployment.json'),catalog=str(cfgdir/'catalog.json'),catalog_sha256=sha(cfgdir/'catalog.json'),
            asset_ids=[a['asset_id'] for a in assets],scope='Local technical catalog only; generator and public rights remain uncleared'))
        print('LOCAL_ACCEPTED_POOL_CATALOG_LOAD_PASS',len(assets));return
    room=prepare_room(inputs.profile,inputs.bindings)
    supports=copy.deepcopy(room.supports)
    for sid,support in supports.items():
        if sid.startswith(('floor_','bed_')):support['source_polygon']=support['polygon'];support['polygon']=support['allowed_region']
    room=dataclasses.replace(room,supports=supports)
    reference=next(x for x in read(REF/'cases/final_case_index.json') if x['version']=='v4_bed');old=read(reference['manifest'])
    # Replace the old pair of generic slippers and bench S0 towel with real
    # personal belongings; avoid stacking an extra quota into the same regions.
    replaced={'quality/slipper/0','quality/slipper/1','quality/s0_towel/1'}
    if any(a['category'] in {'paper','electronics'} for a in selected_assets):replaced.add('quality/book/0')
    requests+=[copy.deepcopy(r) for r in old['requests'] if r['request_id'] not in replaced]
    targets=copy.deepcopy(old['targets']);targets.update(count=len(requests),count_range=[len(requests),len(requests)])
    targets['required_categories']=sorted(set(targets['required_categories'])|cats)
    present_categories={r['category'] for r in requests}
    targets['required_categories']=[c for c in targets['required_categories'] if c in present_categories]
    state_counts={}
    for r in requests:
        key=r['asset_id']+'/'+r['state_id'];state_counts[key]=state_counts.get(key,0)+1
    targets['required_state_counts']={key:min(count,state_counts[key]) for key,count in targets.get('required_state_counts',{}).items() if state_counts.get(key,0)}
    plan=dict(seed=args.seed,scenario='STAYOVER',level='high',requests=requests,targets=targets,budgets=copy.deepcopy(inputs.policy['budgets']),
        assumptions=['CONTROLLED_LOCAL_NO_DISTRIBUTION','ACCEPTED_REAL_BLENDKIT_POOL','FIXED_FORMS_ONLY','V02_SUPPORT_REGIONS'])
    run=ROOT/('runs/local_pool_'+tag);run.mkdir(exist_ok=False);write(run/'request.json',plan);chosen=None
    write(run/'selection.json',dict(seed=args.seed,catalog_pool_ids=[a['asset_id'] for a in assets],selected_ids=sorted(selected_ids),maximum_new=args.max_new,
        support_reservations=dict(bedside_for_large_footwear=reserve_bedside,small_electronics='desk'),scope='Seeded activity/category subset; normal bounded Core placement/static checks still mandatory'))
    write(run/'replacement_policy.json',dict(replaced_request_ids=sorted(replaced),reason='Avoid generic slipper duplication and bench crowding; positions remain sampled, formal baseline unchanged'))
    for ordinal in range(5):
        attempt=run/'attempts'/f'a{ordinal:03d}';attempt.mkdir(parents=True);placements=place_requests(plan,room,inputs.catalog,attempt_ordinal=ordinal);write(attempt/'placement.json',placements)
        if placements['status']!='PASS':continue
        scene=attempt/'scene.usda';write_scene(scene,inputs,placements);manifest=build_manifest(inputs,plan,placements,scene,run.name,attempt_id=attempt.name)
        static=validate_static(scene,manifest,room,inputs);integrity=validate_integrity(inputs,manifest)
        for kind,value in [('static',static),('integrity',integrity)]:write(attempt/(kind+'.json'),value)
        if static['outcome']!='PASS' or integrity['outcome']!='PASS':continue
        replay=replay_manifest(manifest,attempt/'replay',inputs,scene);write(attempt/'replay.json',replay)
        if replay['outcome']!='PASS':continue
        manifest['achieved']=static['metrics']
        for kind,value in [('static',static),('integrity',integrity),('replay',replay)]:manifest['evidence_refs'].append(dict(kind=kind,uri=kind+'.json',sha256=sha(attempt/(kind+'.json')),execution='EXECUTED',outcome=value['outcome'],scope=value['scope'],target_state_digest=manifest['scene']['state_digest'],producer_identity=dict(code_hash=manifest['inputs']['code_hash'])))
        manifest['limits']+=['Local technical pool only; extractable generator and public rights uncleared','STATIC_ONLY; no deformable/dynamic manipulation qualification']
        seal_manifest(manifest,attempt/'manifest.json');chosen=attempt;break
    if chosen is None:raise ValueError('BOUNDED_POOL_PLACEMENT_FAILED; inspect immutable attempts')
    case=dict(outcome='STATIC_INTEGRITY_REPLAY_EXECUTED',config=str(cfgdir/'deployment.json'),manifest=str(chosen/'manifest.json'),scene=str(chosen/'scene.usda'),
        count=len(requests),asset_id=selected_assets[0]['asset_id'],asset_ids=sorted(selected_ids),catalog_pool_ids=[a['asset_id'] for a in assets],scope='LOCAL_POOL_ONLY')
    write(run/'case_index.json',case);write(run/'cases.json',dict(cases=[case]))
    cameras=next(c for c in read(REF/'comparison_index.json')['cases'] if c['version']=='v4_bed')['images']
    write(run/'render_batch.json',dict(cases=[dict(manifest=case['manifest'],cameras={x['view']:x['camera'] for x in cameras if x['view'] in ('overview','floor_foot','floor_bedside','entry_bench')})]))
    print('LOCAL_POOL_STATIC_INTEGRITY_REPLAY_PASS',len(selected_assets),len(requests),str(run))

if __name__=='__main__':main()
