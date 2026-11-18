"""Actual seeded repeat and real-source floating/penetration negative checks."""
import argparse,copy,json
from pathlib import Path
from library import ROOT,read,write
from generate_surface_scenes import load_inputs,Surfaces,place_one,FIRST,validate_scene,write_scene

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);args=p.parse_args();run=args.run.resolve()
    cases=read(run/'cases.json')['cases'];inputs=load_inputs(cases[0]['config'],'hotel705');surfaces=Surfaces(inputs.profile,inputs.bindings)
    records=[a for a in read(ROOT/'registry/assets.json')['assets'] if a.get('local_qualification',{}).get('outcome')=='PASS'];repeats=[]
    for case in cases:
        if case['level']!='low':continue
        manifest=read(case['manifest']);ordinal=int(Path(case['manifest']).parent.name[1:]);objects=[];used=set();contacts=[]
        for index,(sid,cats) in enumerate(FIRST):
            obj,request,contact=place_one(surfaces,inputs,records,used,objects,sid,cats,case['seed'],index,ordinal)
            objects.append(obj);used.add(obj['asset_id']);contacts.append(contact)
        # Core rotated_bounds returns tuples, serialized as arrays in the Manifest.
        assert json.loads(json.dumps(objects))==manifest['objects'],'SAME_SEED_MISMATCH'
        repeats.append(dict(seed=case['seed'],outcome='PASS_EXACT_OBJECTS_AND_MATRICES',objects=len(objects)))
    folder=run/'negative_contact_checks';folder.mkdir(exist_ok=False);negative=[]
    case=cases[0];manifest=read(case['manifest']);contact=read(Path(case['manifest']).parent/'contact_samples.json')['contacts'][0]
    for name,offset in [('floating',.025),('penetrating',-.02)]:
        obj=copy.deepcopy(manifest['objects'][0]);obj['effective']['world_matrix'][3][2]+=offset;obj['after']=copy.deepcopy(obj['effective'])
        scene=folder/(name+'.usda');write_scene(scene,inputs,dict(objects=[obj]));report=validate_scene(scene,[obj],[contact],surfaces,inputs)
        assert report['outcome']=='FAIL' and not report['checks'][0]['tests']['sampled_contact']
        write(folder/(name+'.json'),report);negative.append(dict(test=name,offset_m=offset,expected='FAIL',actual=report['outcome']))
    seeds=sorted({c['seed'] for c in cases})
    a=read(next(c['manifest'] for c in cases if c['level']=='high' and c['seed']==seeds[0]))['objects']
    b=read(next(c['manifest'] for c in cases if c['level']=='high' and c['seed']==seeds[1]))['objects']
    assert [o['effective']['world_matrix'] for o in a]!=[o['effective']['world_matrix'] for o in b]
    write(run/'reproducibility.json',dict(outcome='PASS',same_seed=repeats,different_seed='DIFFERENT_MATRICES',negative_contacts=negative,
        scope='Real qualified Blendkit geometry, no fixture substitution; replay is independently recorded per scene'))
    print('ACTUAL_SEED_REPEAT_AND_CONTACT_NEGATIVES_PASS',repeats,negative)

if __name__=='__main__':main()
