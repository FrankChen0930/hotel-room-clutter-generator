from generate_surface_scenes import *
from density_policy import RANGES,count_for,repeat_cap

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',default='density_v1_a004');parser.add_argument('--seeds',nargs='+',type=int,default=[706,707]);parser.add_argument('--catalog-config',type=Path,default=ROOT/'config/local_pool_batch004_catalog42');parser.add_argument('--hotel-native-only',action='store_true');args=parser.parse_args()
    tag=args.tag;cfgdir=ROOT/'config'/tag;cfgdir.mkdir();original=args.catalog_config.resolve()
    for name in ['deployment.json','profile.json','catalog.json','policy.json','source_lock.json']:write(cfgdir/name,read(original/name))
    catalog=read(cfgdir/'catalog.json');catalog_ids={entry['asset_id'] for entry in catalog['entries']}
    records=[a for a in read(ROOT/'registry/assets.json')['assets'] if a.get('local_qualification',{}).get('outcome')=='PASS' and not a.get('variant_of') and a['asset_id'] in catalog_ids]
    assert records or args.hotel_native_only,'NO_LOCALLY_QUALIFIED_CATALOG_RECORDS'
    if args.hotel_native_only:records=[]
    # Reuse existing internal assets; never count these as BlenderKit acquisitions.
    for row in read(ROOT/'artifacts/legacy_density_pool_a001/index.json'):
        if args.hotel_native_only and row['source_kind']!='EXISTING_ROOM_NOT_NEW_BLENDKIT':continue
        if 'catalog_entry' in row:catalog['entries'].append(row['catalog_entry']) if row['asset_id'] not in [e['asset_id'] for e in catalog['entries']] else None
        else:
            source_path=(ROOT/row['usd_path_relative']).resolve() if row.get('usd_path_relative') else Path(row['usd_path'])
            e=copy.deepcopy(next(e for e in catalog['entries'] if e['origin']=='external'));e.update(asset_id=row['asset_id'],origin='external',source_locator=dict(mount='blendkit_library',path=str(source_path.relative_to(ROOT)).replace('\\','/')),dimensions=row['dimensions_m'],root_prim='/Asset')
            e['states']=[dict(state_id='default',version='1.0',usd_locator_or_native_prim=e['source_locator'],sha256=sha(source_path),units=1,up_axis='Z',pivot=[0,0,0],state_transform=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],visual_bounds=[[-row['dimensions_m'][0]/2,-row['dimensions_m'][1]/2,0],row['dimensions_m']],allowed_pose_tags=['upright'])]
            # Bounds max must be centered, and preserve required contract fields.
            st=e['states'][0];st['visual_bounds'][1]=[row['dimensions_m'][0]/2,row['dimensions_m'][1]/2,row['dimensions_m'][2]]
            st['support_envelope']={'clearance_m':.001};st['alignment']=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];st['footprint']=[[0,0],[1,0],[1,1],[0,1]]
            st['acceptance_refs']=[];st['physics_proxy']={'kind':'none','capability':'STATIC_ONLY','shape_paths':[],'geometry_hash':sha(source_path)}
            e['category']=row['category'];e['dependency_hashes']=[];e['license_scope']='INTERNAL_ONLY'
            existing=next((i for i,item in enumerate(catalog['entries']) if item['asset_id']==e['asset_id']),None)
            if existing is None:catalog['entries'].append(e)
            else:catalog['entries'][existing]=e
            e['provenance']=dict(kind=row['source_kind'],asset_id=row['asset_id'],human_confirmed=False)
            if args.hotel_native_only:e['license_scope']='HOTEL705_USER_CONFIRMED_AUTHOR_LAB_REDISTRIBUTION_PERMISSION'
        records.append(row)
    if args.hotel_native_only:
        assert read(ROOT/'reports/hotel705_redistribution_permission_20261118.json')['outcome']=='USER_CONFIRMED_PERMISSION'
        selected={r['asset_id'] for r in records};catalog['entries']=[e for e in catalog['entries'] if e['asset_id'] in selected]
        lock=read(cfgdir/'source_lock.json');lock['rooms']={k:v for k,v in lock['rooms'].items() if k=='room_hotel'};lock['helpers']=[]
        lock['assets']=[dict(**e['source_locator'],sha256=e['states'][0]['sha256'],bytes=(ROOT/e['source_locator']['path']).stat().st_size) for e in catalog['entries']]
        write(cfgdir/'source_lock.json',lock)
        deployment=read(cfgdir/'deployment.json');deployment['bindings']={k:v for k,v in deployment['bindings'].items() if k in {'room_hotel','blendkit_library'}};write(cfgdir/'deployment.json',deployment)
    policy=read(cfgdir/'policy.json')
    for level in RANGES:
        policy['levels'][level]['count_ranges']['STAYOVER']=list(RANGES[level]);policy['levels'][level]['eligible_categories']=sorted({r['category'] for r in records})
    policy['scenarios']['STAYOVER']['eligible_categories']=sorted({r['category'] for r in records})
    write(cfgdir/'catalog.json',catalog);write(cfgdir/'policy.json',policy)
    inputs=load_inputs(cfgdir/'deployment.json','hotel705');surfaces=Surfaces(inputs.profile,inputs.bindings)
    run=ROOT/'runs'/tag;run.mkdir();write(cfgdir/'density_policy.json',dict(count_ranges=RANGES,scope='Counts are instances, not unique models'))
    cases=[]
    for seed in args.seeds:
      for level in ['low','medium','high']:
        target=count_for(seed,level);folder=run/(level);folder=run/(level+str(seed));folder.mkdir();used_counts=Counter();objects=[];requests=[];contacts=[]
        # Select requested target exactly; do not silently fall back to a smaller count.
        for index in range(target):
            rng=random.Random(str(seed)+level+str(index));supports=['floor_luggage','floor_bedfoot','bed_main','bench','minibar','floor_window_side','bed_single','floor_bedside','floor_desk'];rng.shuffle(supports)
            choices=[r for r in records if used_counts[r['asset_id']]<(20 if args.hotel_native_only else repeat_cap(r))]
            # Smaller objects are necessary at these densities. This is explicit policy.
            choices.sort(key=lambda r:r['dimensions_m'][0]*r['dimensions_m'][1])
            if index<6:
                sid,cats=FIRST[index] if not args.hotel_native_only else (['bench','minibar','floor_luggage','floor_bedside','floor_bedfoot','desk'][index],[r['category'] for r in records]);choices=[r for r in choices if r['category'] in cats]
            else:
                sid=None;cats=[]
            placed=False
            for region in ([sid] if sid else supports):
                try:
                    obj,request,contact=place_one(surfaces,inputs,choices,set(),objects,region,[r['category'] for r in choices],seed,index,0)
                except TypeError:raise
                except ValueError:continue
                used_counts[obj['asset_id']]+=1;objects.append(obj);requests.append(request);contacts.append(contact);placed=True
                break
            if not placed:
                if index>=RANGES[level][0]:
                    write(folder/'capacity_limit.json',dict(requested_sample=target,accepted=index,count_range=RANGES[level]))
                    break
                raise RuntimeError('capacity exhausted below minimum '+str(index))
        target=len(objects)
        scene=folder/'scene.usda';write_scene(scene,inputs,dict(objects=objects))
        static=validate_scene(scene,objects,contacts,surfaces,inputs)
        write(folder/'static.json',static)
        assert static['outcome']=='PASS'
        write(folder/'contact_samples.json',dict(contacts=contacts))
        plan=dict(seed=seed,scenario='STAYOVER',level=level,targets=dict(count=target,count_range=RANGES[level]),requests=requests,budgets=policy['budgets'])
        manifest=build_manifest(inputs,plan,dict(objects=objects),scene,tag)
        integrity=validate_integrity(inputs,manifest);write(folder/'integrity.json',integrity)
        replay=replay_manifest(manifest,folder/'replay',inputs,scene);write(folder/'replay.json',replay)
        seal_manifest(manifest,folder/'manifest.json')
        cases.append(dict(level=level,seed=seed,count=target,manifest=str(folder/'manifest.json'),scene=str(scene),config=str(cfgdir/'deployment.json'),pool_scope='HOTEL705_ORIGINAL_PROPS_ONLY_LIMITED_DIVERSITY' if args.hotel_native_only else 'LOCAL_EXPANDED_BLENDKIT_POOL'))
        print('DENSE',target,static['outcome'],flush=True)
    write(run/'cases.json',dict(cases=cases))

if __name__=='__main__':main()

