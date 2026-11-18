"""Join verified source, conversion, native and Core evidence for local qualification only."""
import argparse
from pathlib import Path
from library import ROOT,read,write,sha,artifact_ok,gate_errors,summarize
from hotel_metadata import enrich

def ref(p):
    p=Path(p).resolve();return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))

def passed(p):
    value=read(p)
    if value.get('outcome')!='PASS':raise ValueError('REPORT_NOT_PASS:'+str(p))
    return value

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--support',type=Path,required=True)
    p.add_argument('--previews',type=Path,nargs='+',required=True);p.add_argument('--receipt',default='batch001_local_qualification.json');args=p.parse_args()
    passed(args.support/'result.json');passed(args.support/'process.json')
    registry=read(ROOT/'registry/assets.json');results=[]
    for index,case in enumerate(read(args.cases)['cases']):
        aid=case['asset_id'];base=aid.removeprefix('bk-');a=next(x for x in registry['assets'] if x['asset_id']==aid)
        previews=next(folder for folder in args.previews if (folder/aid/'visual_review.json').exists())
        visual_path=previews/aid/'visual_review.json';visual=read(visual_path)
        if visual['outcome']!='PASS':results.append(dict(asset_id=aid,outcome=visual['outcome'],reason=visual['observations']));continue
        if a.get('local_qualification',{}).get('outcome')=='PASS':
            assert not gate_errors(a,scope='local')
            saved=read(Path(case['manifest']).parents[2]/'local_qualification.json')
            assert saved['outcome']=='PASS' and saved['manifest']['sha256']==sha(case['manifest'])
            results.append(saved);continue
        duplicate=next((other for other in registry['assets'] if other['asset_id']!=aid
            and other.get('local_qualification',{}).get('outcome')=='PASS'
            and other.get('geometry_identity')==a.get('geometry_identity')),None)
        if duplicate:
            a['variant_of']=duplicate.get('variant_of') or duplicate['asset_id']
            a['geometry_family']=duplicate['geometry_family']
        asset=Path(case['asset']);qual=asset.parent;usd_sha=sha(asset);attempt=Path(case['manifest']).parent
        conversion_path=ROOT/a['evidence']['conversion']['path'];conversion=passed(conversion_path)
        prepdir='prepare_a000' if base=='6d5257a4-4fdf-421d-92b9-e77f941f5187' else read(ROOT/a['processing_job']['path'])['prepare_dir']
        prep_path=ROOT/'artifacts'/base/prepdir/'preparation.json' if prepdir=='prepare_a000' else ROOT/prepdir/'preparation.json'
        prep=passed(prep_path);source=ROOT/a['source']['original_file']['path']
        assert prep['source_sha256']==sha(source) and prep['prepared_sha256']==conversion['source_sha256']
        assert sha(qual/'visual/asset.usdc')==conversion['usd_sha256']
        integrity=passed(qual/'integrity.json');assert all(artifact_ok(x) for x in integrity['dependencies'])
        native=passed(previews/aid/'render.json')
        assert native['usd_sha256']==visual['usd_sha256']==usd_sha and len(native['images'])==2
        assert all(artifact_ok(x) for x in native['images'])
        static=passed(attempt/'static.json');passed(attempt/'integrity.json');replay=passed(attempt/'replay.json')
        support_path=args.support/('case-'+str(index)+'.json');support=passed(support_path)
        assert support['manifest_sha256']==sha(case['manifest'])
        manifest=read(case['manifest']);obj=next(x for x in manifest['objects'] if x['asset_id']==aid)
        checks=[x for x in support['checks'] if x['instance_id']==obj['instance_id']]
        assert checks and all(x['passed'] for x in checks)
        static_check=next(x for x in static['checks'] if x['instance_id']==obj['instance_id'])
        assert static_check['footprint'] and not static_check['collision']
        out=qual/'qualification'
        if out.exists() and any(out.iterdir()):raise ValueError('EXISTING_QUALIFICATION_REQUIRES_REVIEW:'+str(out))
        out.mkdir(exist_ok=True)
        reports={
          'conversion':dict(source=ref(source),preparation=ref(prep_path),original_conversion=ref(conversion_path),proxy=ref(qual/'proxy.json')),
          'integrity':integrity,'native_render':native,'visual':visual,
          'static':dict(core_report=ref(attempt/'static.json'),scene_integrity=ref(attempt/'integrity.json'),check=static_check),
          'support':dict(native_report=ref(support_path),queries=len(checks),checks=checks,scope='Actual native floor collider rays; no dynamics'),
          'catalog':dict(candidate_catalog=ref(Path(case['config']).parent/'catalog.json'),manifest=ref(Path(case['manifest']))),
          'replay':dict(core_report=ref(attempt/'replay.json'),rng_calls=replay['rng_calls'],original_compared=replay['original_compared'])}
        for kind,report in reports.items():
            report={**report,'outcome':'PASS','usd_sha256':usd_sha};path=out/(kind+'.json');write(path,report);a['evidence'][kind]=ref(path)
        a.update(usd=ref(asset),last_completed_stage='VISUAL_ACCEPTED',status='BLOCKED',
            blockers=['EXTRACTABLE_GENERATOR_RIGHTS_UNCLEARED','PUBLIC_REDISTRIBUTION_UNCLEARED'],
            physics=dict(mode='STATIC_ONLY',mass_kg=None,collision_proxy=ref(qual/'proxy.json')),
            local_qualification=dict(outcome='PASS',scene_manifest=ref(Path(case['manifest'])),scope='CONTROLLED_WORKSPACE_NO_DISTRIBUTION'))
        enrich(a);assert not gate_errors(a,scope='local'),gate_errors(a,scope='local')
        assert 'EXTRACTABLE_USD_RIGHTS_UNCLEARED' in gate_errors(a)
        receipt=dict(outcome='PASS',asset_id=aid,usd_sha256=usd_sha,manifest=ref(Path(case['manifest'])),native_support_queries=len(checks),
            static='PASS',integrity='PASS',replay='PASS',native_support='PASS',native_asset_render='PASS',visual='PASS',
            generator_ready=False,public_starter=False,dynamics='NOT_QUALIFIED',
            variant_of=a.get('variant_of'),independent_counted=not bool(a.get('variant_of')))
        write(Path(case['manifest']).parents[2]/'local_qualification.json',receipt)
        results.append(receipt)
        write(ROOT/'registry/assets.json',registry)
    write(ROOT/'reports'/args.receipt,dict(results=results,status=summarize(registry['assets'])))
    print('LOCAL_QUALIFICATION_JOIN_COMPLETE',len(results))

if __name__=='__main__':main()
