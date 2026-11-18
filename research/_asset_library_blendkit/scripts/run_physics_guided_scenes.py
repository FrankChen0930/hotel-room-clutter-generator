"""Bounded physics feedback repairs of existing seeded proposals, never manual poses."""
from generate_surface_scenes import *
import subprocess,os
from check_settled_trajectory import check

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',default='physics_guided_a001');p.add_argument('--proposals',type=Path,default=ROOT/'runs/density_v1_a004');p.add_argument('--resume',action='store_true');a=p.parse_args()
    run=ROOT/'runs'/a.tag;run.mkdir(exist_ok=a.resume)
    previous={(c['level'],c['seed']):c for c in read(run/'cases.json')['cases']} if a.resume else {}
    original=a.proposals.resolve();cases=[]
    records=read(ROOT/'registry/assets.json')['assets']+read(ROOT/'artifacts/legacy_density_pool_a001/index.json')
    for case in read(original/'cases.json')['cases']:
        folder=run/(case['level']+str(case['seed']));folder.mkdir(exist_ok=a.resume)
        inputs=load_inputs(Path(case['config']),'hotel705');surfaces=Surfaces(inputs.profile,inputs.bindings)
        old=read(case['manifest']);objects=copy.deepcopy(old['objects']);requests=copy.deepcopy(old['requests']);contacts=read(Path(case['manifest']).parent/'contact_samples.json')['contacts'];accepted=None
        start=0;prior=previous.get((case['level'],case['seed']))
        if prior and prior.get('accepted'):
            prev=Path(prior['accepted']);strict=check(prev,surfaces)
            if strict['outcome']=='PASS':cases.append(prior);continue
            old=read(prev/'manifest.json');objects=copy.deepcopy(old['objects']);requests=copy.deepcopy(old['requests']);contacts=read(prev/'contact_samples.json')['contacts'];start=int(prev.name[1:])+1
            index_by_path={object_prim(o):i for i,o in enumerate(objects)}
            for index in sorted({index_by_path[x['prim']] for x in strict['issues']}):
                obj=objects[index];record=next(r for r in records if r['asset_id']==obj['asset_id']);remaining=[o for j,o in enumerate(objects) if j!=index]
                replacement,request,contact=place_one(surfaces,inputs,[record],set(),remaining,obj['effective']['support_id'],[record['category']],case['seed'],index,start)
                objects[index]=replacement;requests[index]=request;contacts[index]=contact
            write(prev/'strict_feedback.json',dict(issues=strict['issues'],action='Resample failed same-asset/same-support candidates; retain 12cm displacement and final2s limits'))
        for attempt in range(start,8):
            out=folder/('a'+str(attempt).zfill(3));out.mkdir()
            scene=out/'scene.usda';write_scene(scene,inputs,dict(objects=objects))
            static=validate_scene(scene,objects,contacts,surfaces,inputs);write(out/'static.json',static);assert static['outcome']=='PASS'
            plan=dict(seed=case['seed'],scenario='STAYOVER',level=case['level'],targets=dict(count=len(objects),count_range=old['targets']['count_range'] if 'targets' in old else [len(objects),len(objects)]),requests=requests,budgets=inputs.policy['budgets'])
            manifest=build_manifest(inputs,plan,dict(objects=objects),scene,a.tag,attempt_id=out.name)
            write(out/'integrity.json',validate_integrity(inputs,manifest));write(out/'replay.json',replay_manifest(manifest,out/'replay',inputs,scene));seal_manifest(manifest,out/'manifest.json')
            write(out/'contact_samples.json',dict(contacts=contacts))
            dynamics=out/'dynamics'
            command=[sys.executable,'-B',str(ROOT/'scripts/launch_room_dynamics.py'),'--scene',str(scene),'--manifest',str(out/'manifest.json'),'--output',str(dynamics),'--mode','props_dynamic','--seconds','30']
            result=subprocess.run(command,check=False);report=read(dynamics/'result.json') if (dynamics/'result.json').exists() else dict(outcome='ERROR')
            print('PHYSICS_FEEDBACK',case['level'],case['seed'],attempt,report['outcome'],len(report.get('issues',[])),flush=True)
            if report.get('execution')=='COMPLETED':
                trajectories=read(dynamics/'trajectory.json')['trajectories'];extra=[]
                for obj in objects:
                    path=object_prim(obj);samples=trajectories.get(path,[])
                    if not samples:continue
                    window=[s for s in samples if s['time_s']>=28]
                    norm=lambda x:math.sqrt(sum(v*v for v in x))
                    last=samples[-1]['pose_xyzw'];region=surfaces.specs[obj['effective']['support_id']]['region']
                    point=[[last[0]-.00001,last[1]-.00001],[last[0]+.00001,last[1]-.00001],[last[0],last[1]+.00001]]
                    flags=[]
                    if any(norm(s['velocity'][:3])>.03 or norm(s['velocity'][3:])>.2 for s in window):flags.append('NOT_SETTLED_DURING_FINAL_TWO_SECONDS')
                    if max(math.dist(s['pose_xyzw'][:3],samples[0]['pose_xyzw'][:3]) for s in samples)>.12:flags.append('PLACEMENT_MOVED_MORE_THAN_12CM')
                    if not footprint_supported(dict(status='SUPPORTED',shape='polygon',polygon=region),point,0):flags.append('LEFT_REQUESTED_SUPPORT_REGION')
                    if flags:extra.append(dict(prim=path,issues=flags))
                report['issues']=report['issues']+extra
                if report['issues']:report['outcome']='ISSUES_FOUND'
                write(out/'physics_acceptance.json',dict(outcome=report['outcome'],issues=report['issues'],seconds=30,final_window_seconds=2,linear_limit_mps=.03,angular_limit_radps=.2,max_generated_displacement_m=.12,native_report_sha256=sha(dynamics/'result.json')))
            if report['outcome']=='DIAGNOSTIC_PASS':accepted=out;break
            if report.get('execution')!='COMPLETED':break
            index_by_path={object_prim(o):i for i,o in enumerate(objects)}
            if any(x['prim'] not in index_by_path for x in report['issues']):break
            bad=sorted({index_by_path[x['prim']] for x in report['issues']})
            for index in bad:
                obj=objects[index];record=next(r for r in records if r['asset_id']==obj['asset_id']);remaining=[o for j,o in enumerate(objects) if j!=index]
                replacement,request,contact=place_one(surfaces,inputs,[record],set(),remaining,obj['effective']['support_id'],[record['category']],case['seed'],index,attempt+1)
                objects[index]=replacement;requests[index]=request;contacts[index]=contact
            write(out/'feedback.json',dict(failed_indices=bad,action='Resample same asset on same allowed support using next deterministic attempt',count_unchanged=len(objects)))
        cases.append(dict(**case,accepted=str(accepted) if accepted else None,physics_outcome='PASS' if accepted else 'FAIL',original_manifest=case['manifest']))
        write(run/'cases.json',dict(cases=cases))
    print('PHYSICS_GUIDED_COMPLETE',sum(c['physics_outcome']=='PASS' for c in cases),'/',len(cases),flush=True)

if __name__=='__main__':main()
