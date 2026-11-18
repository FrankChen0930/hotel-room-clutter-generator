"""Curate audited native-room binaries, reproducible source and result metadata."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from library import ROOT,read,write,sha

def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args()
    checkout=a.checkout.resolve();bundle=a.bundle.resolve()
    assert checkout.is_relative_to(ROOT.parent/'_project_delivery')
    assert subprocess.check_output(['git','-C',str(checkout),'branch','--show-current'],text=True).strip()=='main'
    package=read(bundle/'package_manifest.json');relocation=read(bundle/'relocation_verification.json')
    assert package['redistribution']=='HOTEL705_USER_CONFIRMED_AUTHOR_LAB_PERMISSION_ONLY' and relocation['outcome']=='PASS' and len(relocation['roots'])==13
    local_run=ROOT/'runs/report_library_20261119_a000_settled';public_run=ROOT/'runs/public_native_20261118_a000_settled'
    for run in [local_run,public_run]:assert read(run/'verification.json')['outcome']==read(run/'visual_handoff.json')['outcome']=='PASS'
    permission=ROOT/'reports/hotel705_redistribution_permission_20261118.json'
    assert sha(permission)==package['permission_sha256']
    clean=ROOT/'runs/clean_room_report_20261119_a000';assert read(clean/'clean_room_acceptance.json')['outcome']=='PASS'
    # Update engineering source only; keep the already tested portable input/config pins.
    runtime=checkout/'research/_asset_library_blendkit'
    for folder,exts in [('scripts',{'.py','.ps1'}),('tests',{'.py'}),('schemas',{'.json'})]:
        for src in (ROOT/folder).glob('*'):
            if src.is_file() and src.suffix in exts and src.name!='read_reference_pdf_streams.py':copy(src,runtime/folder/src.name)
    for name in ['scenarios.json','rights_scopes.json','requested_count_ranges.json','conversion_job.example.json']:
        copy(ROOT/'config'/name,runtime/'config'/name)
    # Raw local manifests/receipts are retained exactly; delivery map pins rewritten USD hashes.
    evidence=bundle/'evidence';evidence.mkdir(exist_ok=True)
    delivery=[]
    for c in read(public_run/'cases.json')['cases']:
        name=f"{c['level']}_seed_{c['seed']}";d=evidence/name
        for filename in ['manifest.json','physics_evidence.json','native_support.json','scene_static.json']:
            src=Path(c['manifest']).parent/filename
            if src.is_file():copy(src,d/filename)
        native=Path(c['accepted'])/'dynamics/result.json';copy(native,d/'native_dynamics_result.json')
        check=next(x for x in relocation['roots'] if x['path']==f'scenes/{name}.usda')
        delivery.append(dict(seed=c['seed'],level=c['level'],instances=c['count'],scene=f'scenes/{name}.usda',dynamic_scene=f'scenes/{name}_dynamic.usda',original_manifest_sha256=sha(c['manifest']),tested_scene_sha256=sha(c['scene']),delivered_scene_sha256=check['portable_sha256'],equivalence='PASS',physics='PASS',scope='Original manifest and native receipts describe the exact tested source; relative-path package re-encoding is separately verified compositionally equivalent.'))
    for name in ['verification.json','scene_quality_summary.json','visual_handoff.json']:copy(public_run/name,evidence/name)
    copy(permission,bundle/'HOTEL705_PERMISSION.json')
    copy(clean/'clean_room_acceptance.json',evidence/'clean_room_acceptance.json')
    copy(clean/'dynamics/result.json',evidence/'clean_room_native_result.json')
    write(bundle/'delivery_map.json',dict(cases=delivery,scope='Open as complete USD stages; retain all assets. Not a Blendkit model distribution.'))
    (bundle/'USAGE.md').write_text('''# Hotel705 USD examples

Extract the entire archive. In Isaac Sim use File > Open for clean_room.usda or a scenes/*.usda stage. Keep assets/ and all relative paths together. These are complete stages with multiple top-level roots, not individual props to insert using a defaultPrim reference.

The six regular scenes retain physics-settled generated-object poses; the *_dynamic.usda counterparts contain the tested rigid-body configuration. Scene names describe object instance density:Low10-20,Medium30-50,High70-80. No cloth deformation or furniture-layout randomization is included. The original49 dynamic bodies and31 joints remain; fixed walls/furniture supply collision support.

Public examples use only5 native Hotel705 prop source records, with repeated instances. They differ from the richer local102-asset Blendkit research images. No Blendkit model or texture is distributed here. Do not describe repeated instances as independent assets.

HOTEL705_PERMISSION.json records the maintainer's confirmed author/lab redistribution permission. No blanket CC0/MIT license is assigned. Preserve the source attribution in package_manifest.json. Room source:Hotel705 release_v1.0.0/hotel705-random-clutter/assets/room7052/7052_ver3_0925.usda, supplied by the laboratory.

evidence/ retains original manifests and actual30-second/3600-step PhysX acceptance receipts. Their hashes describe tested source stages; relative-path USD repackaging changes file hashes. delivery_map.json and relocation_verification.json link the delivered files to the tested stages and verify exact composed properties/geometry/materials/relationships/physics and internal dependency closure after actual directory relocation. This is not an additional physics simulation or calibrated manipulation certificate.

For new scenes, run research/_asset_library_blendkit/scripts/run_public_workflow.py from the repository using the Isaac Sim Python. That workflow writes new provenance, manifests, physics results and renders; new captures require visual review.
''',encoding='utf8')
    downloads=checkout/'downloads';downloads.mkdir(exist_ok=True);archive=downloads/'hotel705_examples.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in sorted(bundle.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(bundle).as_posix())
    assert archive.stat().st_size<95*1024*1024
    previews=checkout/'docs/previews'
    rows=read(local_run/'scene_quality_summary.json')['cases']
    for level in ['low','medium','high']:
        row=next(c for c in rows if c['level']==level and c['seed']==706)
        copy(ROOT/row['images']['overview'],previews/f'library-{level}706.png')
    for seed in [706,707]:
        row=next(c for c in rows if c['level']=='high' and c['seed']==seed)
        copy(ROOT/row['images']['floor_foot'],previews/f'library-high{seed}-floor.png')
    row=next(c for c in read(public_run/'scene_quality_summary.json')['cases'] if c['level']=='high' and c['seed']==706)
    copy(ROOT/row['images']['overview'],previews/'public-high706.png')
    qualification=read(ROOT/'reports/rigid_expansion_verification.json');accepted={x['asset_id'] for x in qualification['assets'] if x['local_accepted'] and not x.get('variant_of')}
    # Report includes the added cohort; the full record's pinned local qualification also covers baseline.
    assets=[]
    for r in read(ROOT/'registry/assets.json')['assets']:
        s=r['source'];rights=r['rights']
        assets.append(dict(asset_id=r['asset_id'],name=r['name'],author=r.get('author'),source_url=s['url'],version_id=s.get('version_id'),original_sha256=(s.get('original_file') or {}).get('sha256'),license=rights['license'],internal_use=rights.get('internal_use'),extractable_usd=rights.get('extractable_usd'),public_redistribution=rights.get('redistribution'),requires_user_acquisition=rights.get('requires_user_acquisition'),category=r['category'],hotel_use_scenarios=r.get('hotel_use_scenarios'),possible_placement_regions=r.get('possible_placement_regions'),geometry_family=r.get('geometry_family'),visual_family=r.get('visual_family'),variant_of=r.get('variant_of'),physics_qualification=r.get('physics_qualification'),robotics_relevance=r.get('robotics_relevance'),deformation_solved=r.get('deformation_solved'),quality_decision=r['quality_decision'],local_technical_pass=r.get('local_qualification',{}).get('outcome')=='PASS' or r['asset_id'] in accepted))
    write(checkout/'docs/asset_sources.json',dict(assets=assets,scope='Curated identities/rights only. No binary payloads, signed download URLs, raw provider metadata, login data or local file paths.'))
    current={k:read(ROOT/'reports/status.json')[k] for k in ['candidates','acquired','converted','local_technical_ready','local_qualified_variants','generation_ready','public_starter','category_local_technical_ready']}
    write(checkout/'PROJECT_STATUS.json',dict(report_date='2026-11-19',asset_library=current,room_generation='Two room adapters;36 formal cases retained. New full-room simulation evidence is Hotel705 only.',randomization_scope='Clutter only; original furniture layout fixed',soft_object_physics='DEFERRED; fixed shapes only',local_cases=rows,public_cases=delivery,public_native_source_records=5,regression_tests=64,protected_original_files=302,publication='Prepared main-branch delivery; verified remote push receipt is recorded separately.'))
    package_status=dict(outcome='PACKAGE_AND_RELOCATION_VERIFIED',download='downloads/hotel705_examples.zip',bytes=archive.stat().st_size,sha256=sha(archive),stage_count=13,relocation=relocation,rights='HOTEL705_USER_CONFIRMED_AUTHOR_LAB_PERMISSION_ONLY',blendkit_binary_files=0,cases=delivery)
    write(checkout/'docs/PACKAGE_STATUS.json',package_status)
    proof=checkout/'docs/evidence';proof.mkdir(exist_ok=True)
    for label,run in [('local102',local_run),('public_native',public_run)]:
        for name in ['verification.json','visual_handoff.json','scene_quality_summary.json']:copy(run/name,proof/label/name)
    for name in ['clean_room_acceptance.json','geometry_preservation.json']:copy(clean/name,proof/'clean_room'/name)
    copy(permission,proof/'hotel705_permission.json')
    for name in ['asset_funnel_audit.json','visual_review.json','artifact_verification.json']:
        copy(ROOT.parent/'presentation/2026-11-19/weekly-output'/name,proof/'presentation'/name)
    copy(ROOT.parent/'presentation/2026-11-19/weekly-output/hotel_room_weekly_20261119_editable.pptx',checkout/'reports/2026-11-19/hotel_room_weekly_20261119_editable.pptx')
    # Keep raw local backlog reasons private; public explanation is the aggregate only.
    audit_path=proof/'presentation/asset_funnel_audit.json';audit=read(audit_path);audit.pop('rejected_or_pending',None);write(audit_path,audit)
    print('MAIN_DELIVERY_ASSEMBLED',current['local_technical_ready'],'independent assets; ZIP',archive.stat().st_size,'bytes')

if __name__=='__main__':main()
