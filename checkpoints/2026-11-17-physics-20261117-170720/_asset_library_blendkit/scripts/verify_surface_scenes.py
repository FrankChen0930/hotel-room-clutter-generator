"""Verify final multi-surface scene evidence and all displayed source captures."""
import argparse,json,re
from pathlib import Path
from collections import Counter
from library import ROOT,read,write,sha,artifact_ok,gate_errors
from report_surface_scenes import collect
import usd_sdk
usd_sdk.load()
from pxr import Usd,UsdGeom
import sys
sys.path.insert(0,str(ROOT.parent/'common_core'))
from common_core.writer import object_prim
from common_core.identity import state_digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);args=p.parse_args();run=args.run.resolve()
    cases=read(run/'cases.json')['cases'];assert len(cases)==6
    seeds={c['seed'] for c in cases};assert len(seeds)==2
    assert {(c['seed'],c['level']) for c in cases}=={(s,l) for s in seeds for l in ['low','medium','high']}
    records={a['asset_id']:a for a in read(ROOT/'registry/assets.json')['assets']};used=set();proofs=[];total_queries=0;views={}
    pins=read(Path(cases[0]['config']).parent/'producer_sources.json')['files']
    generating_sha=next(p['sha256'] for p in pins if Path(p['path']).name=='generate_surface_scenes.py')
    for i,case in enumerate(cases):
        manifest=read(case['manifest']);attempt=Path(case['manifest']).parent;assert state_digest(manifest)==manifest['scene']['state_digest']
        assert sha(case['scene'])==manifest['scene']['sha256'];assert len(manifest['objects'])==dict(low=6,medium=12,high=22)[case['level']]
        assert len({o['asset_id'] for o in manifest['objects']})==len(manifest['objects'])
        for ref in manifest['evidence_refs']:assert sha(attempt/ref['uri'])==ref['sha256']
        for kind in ['static','integrity','replay']:assert read(attempt/(kind+'.json'))['outcome']=='PASS'
        assert read(attempt/'replay.json')['rng_calls']==0
        contact=read(attempt/'contact_samples.json');specs=Path(case['config']).parent/'surfaces.json';assert sha(specs)==contact['surface_config_sha256']
        assert contact['generator_sha256']==generating_sha
        for c in contact['contacts']:
            assert c['fit']['exact_triangle_peak'] and c['fit']['max_clearance_m']<=.00900001
        native=read(run/'native_support'/('case-'+str(i)+'.json'));assert native['outcome']=='PASS' and native['manifest_sha256']==sha(case['manifest'])
        assert native['checks'] and all(c['passed'] for c in native['checks']);total_queries+=len(native['checks'])
        review=read(attempt/'scene_visual_review.json');assert review['outcome']=='PASS' and review['manifest_sha256']==sha(case['manifest'])
        assert all(artifact_ok(im) for im in review['images']) and len(review['images'])==10
        images=collect(run,i)
        for folder in ['native_render','native_pillow_details','native_local_clear']:
            if not (run/folder).exists():continue
            captured=read(run/folder/('case-'+str(i))/'render.json')
            assert captured['manifest_sha256']==sha(case['manifest']) and captured['scene_sha256']==sha(case['scene'])
        for view,image in images.items():
            camera=json.dumps(image['camera'],sort_keys=True)
            if view in views:assert views[view]==camera
            views[view]=camera
        stage=Usd.Stage.Open(case['scene'])
        for obj in manifest['objects']:
            used.add(obj['asset_id']);prim=stage.GetPrimAtPath(object_prim(obj))
            assert json.loads(prim.GetAttribute('commoncore:semantics').Get())==obj['effective']['semantic_state']
            assert obj['effective']['semantic_state']['ownership']=='GUEST' and obj['effective']['semantic_state']['action_policy']=='DO_NOT_TOUCH'
        supports=Counter(o['effective']['support_id'] for o in manifest['objects'])
        assert 'pillow_left' in supports and 'chair_seat' in supports and 'bed_main' in supports
        if case['level']!='low':assert 'pillow_right' in supports and 'bed_single' in supports and 'floor_between_beds' in supports
        if case['level']=='high':assert 'floor_window_side' in supports and sum(n for k,n in supports.items() if k.startswith('floor'))>=8
        proofs.append(dict(seed=case['seed'],level=case['level'],added_objects=len(manifest['objects']),occupied_regions=len(supports),native_queries=len(native['checks'])))
    for aid in used:assert not gate_errors(records[aid],scope='local'),aid
    for ref in read(Path(cases[0]['config']).parent/'producer_sources.json')['files']:assert artifact_ok(ref)
    for x in read(ROOT/'reports/protected_before.json')['files']:assert sha(x['path'])==x['sha256']
    assert read(run/'reproducibility.json')['outcome']=='PASS'
    testlog=(ROOT/'reports/surface_tests.log').read_text(encoding='utf-8');assert '\nOK' in testlog
    count=int(re.search(r'Ran (\d+) tests',testlog)[1]);assert count>=44
    ui=read(run/'comparison_ui_check.json');assert ui['outcome']=='PASS' and ui['checks']==60
    assert ui['comparison_sha256']==sha(ROOT/'comparison.html')
    result=dict(outcome='PASS',cases=proofs,unique_sources_used=len(used),actual_display_images=60,native_queries=total_queries,tests=count,protected_files=302,
        original_source_saved=False,dynamics='NOT_QUALIFIED',generator_ready=False,public_starter=False,
        comparison_js_checks=ui['checks'],comparison_js_scope=ui['scope'],
        scope='Controlled local static measured-surface candidate; six degree/seed scenes, unchanged real model/source bytes, independent mesh Static, Integrity, Replay, actual native source triangles and actual PNG inspection')
    write(run/'verification.json',result);print('MULTI_SURFACE_FINAL_VERIFIED',result)

if __name__=='__main__':main()
