"""Seeded multi-surface controlled-local scenes; no source edits or hand placed objects."""
import argparse,copy,math,random,sys
from collections import Counter
from pathlib import Path
from library import ROOT,read,write,sha,gate_errors
from integrate_real_backpack import load_inputs,write_scene,build_manifest,seal_manifest,replay_manifest,validate_integrity,REF
from expanded_surfaces import Surfaces
from surface_geometry import rectangle
from common_core.geometry import rotated_bounds,intersects,forbidden_hit
from common_core.adapters import footprint_supported
from common_core.identity import rng_for
from common_core.room import bounds,rows
from common_core.writer import object_prim
from pxr import Usd,UsdGeom,Gf,UsdPhysics

FIRST=[('pillow_left',['electronics','personal']),('chair_seat',['bag','paper','clothing','personal']),('bed_main',['paper','electronics','clothing','personal']),
       ('floor_luggage',['luggage','bag']),('floor_bedside',['footwear']),('desk',['electronics'])]
MIDDLE=[('bed_single',['clothing','towel','personal']),('bench',['toiletry','paper','personal']),('floor_bedfoot',['bag','clothing']),
        ('pillow_right',['electronics','personal']),('minibar',['toiletry','food']),('floor_between_beds',['footwear'])]
LAST=[('bed_main',['paper','electronics','clothing','personal']),('bed_single',['paper','clothing','towel','personal']),('floor_window_side',['bag','clothing']),
      ('floor_desk',['footwear','bag']),('floor_window_side',['clothing','towel']),('floor_luggage',['bag','clothing']),
      ('bench',['toiletry','food','personal']),('minibar',['toiletry','food']),('floor_between_beds',['footwear']),('bed_main',['clothing','paper','electronics','personal'])]

def eligible(a,sid,categories):
    if a['category'] not in categories:return False
    x,y,z=a['dimensions_m']
    if sid.startswith('pillow'):return a['category'] in {'electronics','personal'} and max(x,y)<=.15 and min(x,y)<=.055 and z<=.065
    if sid.startswith('bed_') and a['category'] not in {'paper','electronics','clothing','towel','bag','personal'}:return False
    if a['category']=='electronics' and max(x,y)<=.15 and min(x,y)<=.055 and z<=.065:return False
    if sid=='chair_seat':return min(x,y)<.27 and max(x,y)<.38
    if sid.startswith('bed_') and a['category']=='electronics':return z<.30
    return True

def place_one(surfaces,inputs,records,used,objects,sid,categories,seed,index,attempt):
    rng=rng_for(seed,'expanded_surfaces','slot/'+str(index),attempt)
    choices=[a for a in records if a['asset_id'] not in used and eligible(a,sid,categories)];rng.shuffle(choices)
    region=surfaces.specs[sid]['region'];lo=[min(p[i] for p in region) for i in range(2)];hi=[max(p[i] for p in region) for i in range(2)]
    entries={e['asset_id']:e for e in inputs.catalog['entries']};failures=Counter();samples=0
    for a in choices:
        state=entries[a['asset_id']]['states'][0];box=state['visual_bounds']
        for _ in range(220):
            samples+=1;x=rng.uniform(lo[0],hi[0]);y=rng.uniform(lo[1],hi[1]);yaw=rng.uniform(-math.pi,math.pi)
            footprint,_=rotated_bounds(box,yaw,x,y,0)
            if not footprint_supported(dict(status='SUPPORTED',shape='polygon',polygon=region),footprint,.006):failures['edge']+=1;continue
            fit=surfaces.fit(sid,box,x,y,yaw)
            if not fit:failures['curvature_or_hole']+=1;continue
            fit=surfaces.fit(sid,box,x,y,yaw,exact=True)
            if not fit:failures['exact_peak_or_dense_relief']+=1;continue
            z=fit['z']+.001-box[0][2];footprint,world_box=rotated_bounds(box,yaw,x,y,z)
            if forbidden_hit(world_box,inputs.profile['forbidden_regions']):failures['forbidden']+=1;continue
            if any(intersects(world_box,o['expected_bounds'],.006) for o in objects):failures['other_object']+=1;continue
            hit=surfaces.source_collision(world_box,sid)
            if hit:failures['source_obstacle']+=1;continue
            base=Gf.Matrix4d(*[v for row in state['state_transform'] for v in row])
            matrix=base*Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0,0,1),math.degrees(yaw)))*Gf.Matrix4d().SetTranslate((x,y,z))
            semantics=dict(ownership='GUEST',action_policy='DO_NOT_TOUCH',condition='IN_USE',hotel_activity='travel_stayover')
            effective=dict(world_matrix=rows(matrix),state_id=state['state_id'],support_id=sid,semantic_state=semantics,body_mode='kinematic')
            rid='expanded/slot/'+str(index)
            obj=dict(instance_id=rid,request_id=rid,asset_id=a['asset_id'],state_sha256=state['sha256'],origin='external',source_object_id=None,native_prim=None,
                before=dict(exists=False),after=copy.deepcopy(effective),effective=effective,expected_bounds=world_box,footprint=footprint)
            req=dict(request_id=rid,asset_id=a['asset_id'],category=a['category'],state_id=state['state_id'],origin='external',source_object_id=None,
                allowed_support_ids=[sid],semantic_state=semantics)
            return obj,req,dict(instance_id=rid,asset_id=a['asset_id'],support_id=sid,x=x,y=y,yaw=yaw,fit=fit,samples=samples,rejections=dict(failures))
    raise ValueError('SURFACE_PLACEMENT_EXHAUSTED:'+sid+':'+str(dict(failures)))

def validate_scene(scene,objects,contacts,surfaces,inputs):
    stage=Usd.Stage.Open(str(scene));cache=UsdGeom.BBoxCache(0,['default','render','proxy']);checks=[];boxes=[]
    for obj,contact in zip(objects,contacts):
        prim=stage.GetPrimAtPath(object_prim(obj));actual=rows(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));box=bounds(prim,cache)
        delta=max(abs(actual[i][j]-obj['effective']['world_matrix'][i][j]) for i in range(4) for j in range(4))
        sid=contact['support_id'];entry=next(e for e in inputs.catalog['entries'] if e['asset_id']==obj['asset_id']);state=entry['states'][0]
        fresh=surfaces.fit(sid,state['visual_bounds'],contact['x'],contact['y'],contact['yaw'],exact=True)
        # Independent USD readback, independently recomputed source heights and source obstacles.
        tests=dict(matrix=delta<1e-8,footprint=footprint_supported(dict(status='SUPPORTED',shape='polygon',polygon=surfaces.specs[sid]['region']),obj['footprint'],0),
            sampled_contact=bool(fresh) and abs(box[0][2]-(fresh['z']+.001))<.0001,
            no_source_penetration=not surfaces.source_collision(box,sid),no_object_overlap=not any(intersects(box,b) for b in boxes),
            allowed_region=not forbidden_hit(box,inputs.profile['forbidden_regions']),kinematic=UsdPhysics.RigidBodyAPI(prim).GetKinematicEnabledAttr().Get() is True)
        boxes.append(box);checks.append(dict(instance_id=obj['instance_id'],support_id=sid,tests=tests,actual_bounds=box,
            max_sampled_footprint_gap_m=None if not fresh else fresh['max_clearance_m']))
    unresolved=__import__('pxr',fromlist=['UsdUtils']).UsdUtils.ComputeAllDependencies(str(scene))[2]
    return dict(outcome='PASS' if not unresolved and all(all(c['tests'].values()) for c in checks) else 'FAIL',execution='EXECUTED',checks=checks,
        unresolved=list(map(str,unresolved)),scope='Independent candidate adapter: USD matrix/bounds readback,81 unchanged source mesh heights per footprint,<=9mm conservative sampled gap, source triangle AABB obstacles, overlaps, region, kinematic state; no dynamics')

def generate(args):
    cfgdir=ROOT/'config'/args.tag;cfgdir.mkdir(exist_ok=False)
    original=ROOT/'config/local_pool_batch004_catalog42'
    for name in ['deployment.json','profile.json','catalog.json','policy.json','source_lock.json']:write(cfgdir/name,read(original/name))
    profile=read(cfgdir/'profile.json');profile['profile_version']='measured-surfaces-'+args.tag
    profile['provenance']['expanded_surface_adapter']=dict(path='scripts/expanded_surfaces.py',sha256=sha(ROOT/'scripts/expanded_surfaces.py'))
    policy=read(cfgdir/'policy.json');policy['release_frozen']=False;policy['version']='measured-surfaces-local-'+args.tag
    records=[a for a in read(ROOT/'registry/assets.json')['assets'] if a.get('local_qualification',{}).get('outcome')=='PASS']
    for a in records:assert not gate_errors(a,scope='local'),a['asset_id']
    categories=sorted({a['category'] for a in records})
    for level,n in [('low',6),('medium',12),('high',22)]:
        policy['levels'][level]['eligible_categories']=categories;policy['levels'][level]['count_ranges']['STAYOVER']=[n,n]
        policy['levels'][level]['allowed_states']={};policy['levels'][level]['required_state_counts']={}
    policy['scenarios']['STAYOVER']['eligible_categories']=categories
    write(cfgdir/'profile.json',profile);write(cfgdir/'policy.json',policy)
    inputs=load_inputs(cfgdir/'deployment.json','hotel705');surfaces=Surfaces(profile,inputs.bindings)
    write(cfgdir/'surfaces.json',surfaces.record())
    run=ROOT/'runs'/args.tag;run.mkdir(exist_ok=False);cases=[];render_cases=[]
    cameras={im['view']:im['camera'] for c in read(REF/'comparison_index.json')['cases'] if c['version']=='v4_bed' for im in c['images']}
    cameras.update(bed_surface=dict(eye=[-.1,-6.3,2.25],target=[1.6,-4.95,.68],focal=22),pillows=dict(eye=[.95,-4.95,1.65],target=[2.2,-4.95,.92],focal=28),
        chair_seat=dict(eye=[-.02,-6.5,1.35],target=[-.5,-7.34,.48],focal=35),single_bed=dict(eye=[-.15,-2.7,1.65],target=[1.4,-3.22,.51],focal=25))
    for seed in args.seeds:
      for level,templates in [('low',FIRST),('medium',FIRST+MIDDLE),('high',FIRST+MIDDLE+LAST)]:
        folder=run/(level+'_'+str(seed));folder.mkdir();chosen=None
        for ordinal in range(6):
            attempt=folder/('a'+str(ordinal).zfill(3));attempt.mkdir();objects=[];requests=[];contacts=[];used=set()
            try:
                for index,(sid,cats) in enumerate(templates):
                    obj,request,contact=place_one(surfaces,inputs,records,used,objects,sid,cats,seed,index,ordinal)
                    objects.append(obj);requests.append(request);contacts.append(contact);used.add(obj['asset_id'])
                scene=attempt/'scene.usda';write_scene(scene,inputs,dict(objects=objects))
                static=validate_scene(scene,objects,contacts,surfaces,inputs);write(attempt/'static.json',static)
                if static['outcome']!='PASS':raise ValueError('INDEPENDENT_MESH_STATIC_FAILED')
                plan=dict(seed=seed,scenario='STAYOVER',level=level,requests=requests,targets=dict(count=len(objects),count_range=[len(objects),len(objects)],required_categories=sorted({r['category'] for r in requests}),required_state_counts={}),budgets=policy['budgets'])
                manifest=build_manifest(inputs,plan,dict(objects=objects),scene,args.tag,attempt_id=attempt.name)
                manifest['achieved'].update(unique_asset_ids=len(used),surface_counts=dict(Counter(o['effective']['support_id'] for o in objects)))
                manifest['limits']=['CONTROLLED_LOCAL_NO_DISTRIBUTION','STATIC_ONLY: no dynamic, deformation or manipulation qualification','Candidate measured mesh surface validator; formal V1 planar support scope unchanged']
                write(attempt/'contact_samples.json',dict(contacts=contacts,surface_config_sha256=sha(cfgdir/'surfaces.json'),generator_sha256=sha(__file__)))
                integrity=validate_integrity(inputs,manifest);write(attempt/'integrity.json',integrity);assert integrity['outcome']=='PASS'
                replay=replay_manifest(manifest,attempt/'replay',inputs,scene);write(attempt/'replay.json',replay);assert replay['outcome']=='PASS'
                for kind in ['static','integrity','replay','contact_samples']:
                    manifest['evidence_refs'].append(dict(kind=kind,uri=kind+'.json',sha256=sha(attempt/(kind+'.json')),execution='EXECUTED',outcome='PASS',scope='Controlled local measured-surface evidence',target_state_digest=manifest['scene']['state_digest'],producer_identity=dict(code_hash=manifest['inputs']['code_hash'])))
                seal_manifest(manifest,attempt/'manifest.json');chosen=attempt;break
            except Exception as e:
                write(attempt/'failure.json',dict(outcome='FAIL',reason=str(e),placed=len(objects)));print('BOUNDED_SURFACE_ATTEMPT',seed,level,ordinal,str(e),flush=True)
        if chosen is None:raise ValueError('LEVEL_FAILED:'+level+':'+str(seed))
        case=dict(level=level,seed=seed,config=str(cfgdir/'deployment.json'),manifest=str(chosen/'manifest.json'),scene=str(chosen/'scene.usda'),asset_id=objects[0]['asset_id'],asset_ids=sorted(used),count=len(objects),scope='CONTROLLED_LOCAL_MEASURED_SURFACES')
        cases.append(case);render_cases.append(dict(manifest=case['manifest'],cameras={v:cameras[v] for v in ['overview','floor_foot','bed_surface','pillows','chair_seat','single_bed','entry_bench']}))
        write(folder/'asset_usage.json',dict(assets=[dict(asset_id=o['asset_id'],name=next(a['name'] for a in records if a['asset_id']==o['asset_id']),source_url=next(a['source']['url'] for a in records if a['asset_id']==o['asset_id']),support_id=o['effective']['support_id']) for o in objects],surface_counts=manifest['achieved']['surface_counts']))
        print('MEASURED_SURFACE_SCENE',level,seed,len(objects),manifest['achieved']['surface_counts'],flush=True)
    write(run/'cases.json',dict(cases=cases));write(run/'render_batch.json',dict(cases=render_cases));write(run/'surface_config.json',surfaces.record())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--seeds',nargs='+',type=int,default=[706,707]);generate(p.parse_args())
