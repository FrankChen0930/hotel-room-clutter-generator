"""Evidence-only index; authoritative effective state stays in each manifest."""
from pathlib import Path
from .batch import validate_spec
from .contracts import load_json
from .identity import sha256_file
from .replay import load_manifest
from .room import load_inputs
from .visual import verify_review


def final_index(spec, batch_root, support_root, review_root, config):
    cases=validate_spec(spec)
    expected={(r,s,l,n) for r in ['hotel705','yazhi'] for s in ['STAYOVER','CHECKOUT'] for l in ['low','medium','high'] for n in [706,707,708]}
    actual={(c['room'],c['scenario'],c['level'],c['seed']) for c in cases}
    if len(cases)!=36 or actual!=expected:raise ValueError('DELIVERY_FORMAL36_KEYS')
    source_index=load_json(Path(batch_root)/'batch_index.json')
    if source_index['outcome']!='PASS' or len(source_index['cases'])!=36:raise ValueError('DELIVERY_GENERATION_INCOMPLETE')
    process=load_json(Path(support_root)/'process.json');aggregate=load_json(Path(support_root)/'result.json')
    if process['native_exit_code']!=0 or process['termination_reason'] or aggregate['outcome']!='PASS' or len(aggregate['results'])!=36:raise ValueError('DELIVERY_SUPPORT_INCOMPLETE')
    records=[];cache={};coverage={};states={}
    for index,case in enumerate(cases):
        room=case['room'];cache.setdefault(room,load_inputs(config,room))
        path=Path(batch_root)/case['case_key']/'attempts/a000/manifest.json';manifest=load_manifest(path,cache[room])
        key=manifest['inputs']
        if (key['seed'],key['scenario'],key['level'])!=(case['seed'],case['scenario'],case['level']):raise ValueError('DELIVERY_CASE_IDENTITY')
        refs={ref['kind']:ref for ref in manifest['evidence_refs']};layers={}
        for kind in ['static','integrity','replay']:
            ref=refs[kind];report=load_json(path.parent/ref['uri'])
            if ref['outcome']!='PASS' or report['execution']!='EXECUTED' or report['outcome']!='PASS':raise ValueError('DELIVERY_'+kind.upper())
            layers[kind]=dict(execution='EXECUTED',outcome='PASS',path=str(path.parent/ref['uri']),sha256=ref['sha256'])
        support_path=Path(support_root)/('case-'+str(index)+'.json');support=load_json(support_path)
        if support['outcome']!='PASS' or support['manifest_sha256']!=sha256_file(path) or support['target_state_digest']!=manifest['scene']['state_digest'] or support['scene_sha256']!=manifest['scene']['sha256']:raise ValueError('DELIVERY_SUPPORT_IDENTITY')
        layers['support']=dict(execution='EXECUTED',outcome='PASS',path=str(support_path),sha256=sha256_file(support_path))
        review=verify_review(Path(review_root)/(case['case_key']+'.json'),path)
        layers['visual']=dict(execution='EXECUTED',outcome='PASS',path=review['path'],sha256=review['sha256'],reviewer=review['reviewer'])
        layers['limited_dynamic_physics']=dict(execution='NOT_RUN',outcome='UNKNOWN',scope='No whole-scene qualification; WU-21 named target assessments separate')
        layers['delivery_reproducibility']=dict(execution='NOT_RUN',outcome='UNKNOWN',scope='Author relocation WU-18 passed; independent researcher receipt remains WU-22')
        records.append(dict(**case,manifest=str(path),manifest_sha256=sha256_file(path),state_digest=manifest['scene']['state_digest'],layers=layers))
        coverage.setdefault((room,case['scenario'],case['level']),[]).append(manifest['achieved']['coverage'])
        states.setdefault((room,case['scenario']),set()).update(o['effective']['state_id'] for o in manifest['objects'] if o['asset_id']=='s0_towel')
    means=[]
    for room in ['hotel705','yazhi']:
        for scenario in ['STAYOVER','CHECKOUT']:
            values=[sum(coverage[(room,scenario,l)])/3 for l in ['low','medium','high']]
            if not values[0]<values[1]<values[2]:raise ValueError('DELIVERY_LEVEL_MEANS')
            if not {'folded','loose'}<=states[(room,scenario)]:raise ValueError('DELIVERY_S0_STATES')
            means.append(dict(room=room,scenario=scenario,coverage_means=values))
    return dict(schema='DeliveryIndex/1',outcome='ENGINEERING_SCENES_PASS',cases=records,level_means=means,
        scope='WU-20 applicable scene gates only; limited dynamics WU-21 and independent handoff WU-22 remain separate')
