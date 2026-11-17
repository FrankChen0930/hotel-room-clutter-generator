"""Promote technical evidence only after real local checks pass; never clears generator/public rights."""
from pathlib import Path
from library import ROOT,read,write,sha,artifact_ok,gate_errors

BASE='fa971768-8e7e-49dd-93e5-c225b578899e';AID='bk-'+BASE
run=ROOT/'runs/real_backpack_hotel705_stayover_high_706_a002';case=read(run/'case_index.json');attempt=Path(case['manifest']).parent
asset=Path(case['asset']);usd_sha=sha(asset);qual=asset.parent;out=qual/'qualification';out.mkdir(exist_ok=False)
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
def verified_report(p):
    report=read(p)
    if report['outcome']!='PASS':raise ValueError('REPORT_NOT_PASS:'+str(p))
    return report

registry=read(ROOT/'registry/assets.json');a=next(x for x in registry['assets'] if x['asset_id']==AID)
original=ROOT/a['source']['original_file']['path'];prep=verified_report(ROOT/'artifacts'/BASE/'prepare_a000/preparation.json')
conversion=verified_report(ROOT/'artifacts'/BASE/'convert_a000/conversion.json');integrity=verified_report(qual/'integrity.json')
native=verified_report(ROOT/'reports/native_real_backpack_a001/render.json')
assert prep['original_sha256']==sha(original) and prep['prepared_sha256']==conversion['source_sha256']
assert sha(qual/'visual/asset.usdc')==conversion['usd_sha256']
assert native['usd_sha256']==usd_sha and all(artifact_ok(x) for x in native['images'])
assert all(artifact_ok(x) for x in integrity['dependencies'])
static=verified_report(attempt/'static.json');core_integrity=verified_report(attempt/'integrity.json');replay=verified_report(attempt/'replay.json')
support=verified_report(run/'native_support/case-0.json');verified_report(run/'native_support/result.json')
manifest=read(case['manifest']);obj=next(x for x in manifest['objects'] if x['asset_id']==AID)
support_checks=[x for x in support['checks'] if x['instance_id']==obj['instance_id']]
assert support_checks and all(x['passed'] for x in support_checks)
assert support['manifest_sha256']==sha(case['manifest'])
static_check=next(x for x in static['checks'] if x['instance_id']==obj['instance_id'])
assert static_check['footprint'] and not static_check['collision']
reports={
 'conversion':dict(source_sha256=sha(original),preparation=ref(ROOT/'artifacts'/BASE/'prepare_a000/preparation.json'),
    original_conversion=ref(ROOT/'artifacts'/BASE/'convert_a000/conversion.json'),proxy=ref(qual/'proxy.json'),
    scope='Actual official raw source -> one high LOD -> exact Base Color bake -> USD -> conservative static proxy wrapper'),
 'integrity':integrity,
 'native_render':native,
 'visual':dict(reviewer='Codex visual inspection of both actual Isaac PNGs',images=native['images'],
    observations=['Recognizable fabric/leather backpack; original scanned texture visible','No missing materials, UV or placeholder geometry',
    'Fixed scanned lying form; some close-up texture softness; accepted for floor/bench clutter, not hero macro use'],
    scope='Controlled local asset preview acceptance; full room comparison separate'),
 'static':dict(core_report=ref(attempt/'static.json'),scene_integrity=ref(attempt/'integrity.json'),check=static_check,
    scope='Composed Hotel705 STAYOVER/high/706; all 26 objects pass static and locked dependency integrity'),
 'support':dict(native_report=ref(run/'native_support/case-0.json'),queries=len(support_checks),checks=support_checks,
    scope='Executed native source-floor collider rays at center/corners/midpoints; conservative support envelope; no dynamics'),
 'catalog':dict(candidate_catalog=ref(ROOT/'config/local_backpack_a002/catalog.json'),manifest=ref(Path(case['manifest'])),
    scope='Independent Common Core candidate schema/load validation and actual 26-object scene integration; LOCAL ONLY'),
 'replay':dict(core_report=ref(attempt/'replay.json'),rng_calls=replay['rng_calls'],original_compared=replay['original_compared'],
    scope='Actual effective poses, geometry/material/semantics and dependency replay against original candidate scene')}
for kind,report in reports.items():
    report.update(outcome='PASS',usd_sha256=usd_sha)
    path=out/(kind+'.json');write(path,report);a['evidence'][kind]=ref(path)
a.update(usd=ref(asset),last_completed_stage='VISUAL_ACCEPTED',status='BLOCKED',
    blockers=['EXTRACTABLE_GENERATOR_RIGHTS_UNCLEARED','PUBLIC_REDISTRIBUTION_UNCLEARED'],
    physics=dict(mode='STATIC_ONLY',mass_kg=None,collision_proxy=ref(qual/'proxy.json')))
a['local_qualification']=dict(outcome='PASS',scene_manifest=ref(Path(case['manifest'])),scope='CONTROLLED_WORKSPACE_NO_DISTRIBUTION')
a['discovery_quality']['visual_acceptance']='ACCEPTED_LOCAL_PREVIEW'
a['discovery_quality']['uniqueness']='One official base ID; high source LOD only; normalized geometry fingerprint recorded'
errors=gate_errors(a,scope='local')
if errors:raise ValueError('LOCAL_GATE_ERRORS:'+str(errors))
assert 'EXTRACTABLE_USD_RIGHTS_UNCLEARED' in gate_errors(a)
write(ROOT/'registry/assets.json',registry)
write(run/'local_qualification.json',dict(outcome='PASS',asset_id=AID,usd_sha256=usd_sha,manifest=ref(Path(case['manifest'])),
    static='PASS',integrity='PASS',replay='PASS',native_support='PASS',native_asset_render='PASS',native_support_queries=len(support_checks),
    generator_ready=False,public_starter=False,dynamics='NOT_QUALIFIED',scope='All technical evidence passed for controlled local research; RF output/distribution not cleared'))
write(ROOT/'registry/latest_local_scene.json',case)
write(ROOT/'sources/intake_user_002/recovery.json',dict(outcome='PASS_RECOVERED_AND_LOCALLY_QUALIFIED',asset_id=AID,
    original_gui_status_preserved=True,qualification=ref(run/'local_qualification.json'),user_action='No re-download or further GUI action required'))
print('REAL_BACKPACK_LOCAL_TECHNICAL_READY; GENERATOR/PUBLIC STILL BLOCKED',len(support_checks),'native support rays')
