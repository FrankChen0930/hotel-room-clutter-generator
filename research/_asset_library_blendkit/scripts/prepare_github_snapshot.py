"""Curated code/status snapshot. Deliberately excludes models, credentials and SDKs."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
from library import ROOT,read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();workspace=ROOT.parent;out=a.output.resolve()
    assert out.is_relative_to(workspace/'_project_delivery');out.mkdir(parents=True,exist_ok=False);inventory=[]
    def copy(source,target):
        dest=out/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        inventory.append(dict(path=target.replace('\\','/'),source=str(source.relative_to(workspace)).replace('\\','/'),sha256=sha(dest),bytes=dest.stat().st_size))
    tracked=subprocess.run(['git','-C',str(workspace/'common_core'),'-c','safe.directory=C:/hotel_room/common_core','ls-files'],capture_output=True,text=True,check=True).stdout.splitlines()
    for name in tracked:
        if name in ['config/deployment.local.json','AGENTS.md']:continue
        source=workspace/'common_core'/name
        if source.is_file():copy(source,'common_core/'+name)
    for folder,extensions in [('scripts',{'.py','.ps1'}),('tests',{'.py'}),('schemas',{'.json'})]:
        for source in sorted((ROOT/folder).glob('*')):
            if source.is_file() and source.suffix in extensions and source.name!='read_reference_pdf_streams.py':copy(source,'_asset_library_blendkit/'+folder+'/'+source.name)
    for name in ['scenarios.json','rights_scopes.json','requested_count_ranges.json','conversion_job.example.json']:
        copy(ROOT/'config'/name,'_asset_library_blendkit/config/'+name)
    for source in sorted((workspace/'_common_core_planning').glob('*.md')):copy(source,'docs/common_core/'+source.name)
    plan=ROOT/'.planning/2026-11-15-blendkit-library'
    for name in ['task_plan.md','progress.md','findings.md']:copy(plan/name,'docs/asset_library_plan/'+name)
    model_metadata=[]
    for item in read(ROOT/'registry/assets.json')['assets']:
        s=item.get('source',{});rights=item.get('rights',{})
        model_metadata.append(dict(asset_id=item['asset_id'],name=item.get('name'),author=item.get('author'),source_url=s.get('url'),source_asset_id=s.get('asset_base_id'),source_version_id=s.get('version_id'),original_sha256=s.get('original_file',{}).get('sha256') if isinstance(s.get('original_file'),dict) else None,category=item.get('category'),geometry_family=item.get('geometry_family'),visual_family=item.get('visual_family'),robotics_relevance=item.get('robotics_relevance'),license=rights.get('license'),internal_use=rights.get('internal_use'),extractable_usd=rights.get('extractable_usd'),redistribution=rights.get('redistribution'),requires_user_acquisition=rights.get('requires_user_acquisition'),last_completed_stage=item.get('last_completed_stage'),status=item.get('status'),local_technical_pass=item.get('local_qualification',{}).get('outcome')=='PASS'))
    write(out/'metadata/asset_sources.json',dict(assets=model_metadata,scope='Source identities and rights metadata only. No model, texture, signed download URL or login data.'))
    run=ROOT/'runs/physics_settled_a002';quality=read(run/'scene_quality_summary.json');verification=read(run/'verification.json')
    status=read(ROOT/'reports/status.json')
    counts={key:status[key] for key in ['target','candidates','acquired','converted','generation_ready','public_starter','local_technical_ready','category_local_technical_ready']}
    summary=dict(checkpoint_date='2026-11-17',repository='https://github.com/FrankChen0930/hotel-room-clutter-generator',common_core_status='LOCAL_RC_COMPLETE',asset_library=counts,physics_scope='Full-room rigid surrogate stability of exact six cases, not calibrated manipulation or flexible-body qualification',original_dynamic_bodies=49,original_authored_joints=31,nominal_seconds_per_case=30,nominal_steps_per_case=3600,soft_object_validation='DEFERRED_BY_USER; fixed visual forms retained, no deformable acceptance',cases=[{k:c[k] for k in ['level','seed','count','unique_asset_ids','category_counts','surface_counts','physics','registered_bodies','native_steps','visual_review']} for c in quality['cases']],regression_tests=49,protected_files=verification['protected'],source_results_local_run='runs/physics_settled_a002',excluded='Original/converted models, textures, SDKs, add-on/profile/cache, raw third-party metadata, original PDF, local scenes and all credentials',github_push_status='NOT_PUSHED')
    summary['github_push_status']='PREPARED_CHECKPOINT; remote push receipt is recorded separately'
    write(out/'PROJECT_STATUS.json',summary)
    sensitivity=read(run/'sensitivity.json');write(out/'evidence/sensitivity.json',sensitivity)
    write(out/'evidence/verification_summary.json',dict(outcome=verification['outcome'],tests=verification['tests'],protected=verification['protected'],cases=[{k:c[k] for k in ['level','seed','count','outcome','manifest_sha256','scene_sha256','dynamic_scene_sha256']} for c in verification['cases']],evidence_run_sha256=sha(run/'verification.json'),scope=verification['scope']))
    write(out/'evidence/native_render_summary.json',{k:v for k,v in read(run/'native_render_a001/process.json').items() if k!='command'})
    (out/'README.md').write_text('''# Hotel Room Clutter Generation — research checkpoint

Checkpoint:2026-11-17. See PROJECT_STATUS.json for precise scope and counts.

This repository snapshot contains Common Core V1 source, Blendkit library/physics pipeline source and tests, source/license metadata, planning records and selected evidence summaries. It is not a self-contained asset distribution or a complete binary workspace backup.

## Current results

- Common Core V1: LOCAL_RC_COMPLETE; protected baseline and36 formal cases retained locally.
- Blendkit:384 candidates,187 acquired,48 converted,42 locally accepted;0 GENERATION_READY and0 publicly cleared Starter assets. These gates are distinct.
- Seed706 Low/Medium/High:15/32/72 instances; Seed707:13/49/73. Counts are instances, not independent source models.
- Six exact full-room CPU PhysX nominal runs:30s,3600 steps,49 original dynamic bodies and31 source joints plus all generated props. Two additional High mass/COM trials passed. These are rigid surrogates with estimated parameters.
- Soft-object physics validation is deferred by user decision. Cloth/bags/pillows remain fixed visual forms; no deformable simulation or robot manipulation qualification is claimed.
-30 native captures reviewed locally,49 regression tests passed,302 protected files unchanged.

## Layout and prerequisites

Keep common_core/ and _asset_library_blendkit/ as siblings. Python scripts target the existing Windows Blender and Isaac Sim6.0.0-rc.59 environment. See source for current SDK paths. Native runs require separately and legally acquired room/asset inputs and local deployment bindings; those dependencies are intentionally absent here. This source snapshot alone cannot reproduce the full room render.

Pure engineering checks on the original SDK environment:

```powershell
& C:\\isaac_sim\\kit\\python\\python.exe -B -m unittest discover -s _asset_library_blendkit/tests -p 'test_*.py'
```

With local legal assets/configuration available, the complete independent candidate entry is _asset_library_blendkit/scripts/run_density_physics_pipeline.py --tag NEW_TAG --seeds706707 (pass706 and707 as separate arguments). Review actual images before handoff. Never infer public redistribution or flexible-object qualification from a local physics PASS.

## Rights and omissions

No original Blendkit .blend, converted USD, texture, Hotel705/YAZHI source asset, SDK, add-on, login profile, raw cache or paper PDF is included. Obtain dependencies legally through their original sources. Source/license metadata is in metadata/asset_sources.json; unknown extractable-USD/redistribution rights stay unknown. No blanket license is assigned to third-party materials or to this checkpoint.

Some source scripts reference intentionally excluded local run/config artifacts. Evidence JSONs here are summaries and hashes, not claims that the omitted runtime artifacts are bundled. Source attribution and binary qualification gates remain independent.
'''.replace('--seeds706707','--seeds 706 707'),encoding='utf-8')
    (out/'.gitignore').write_text('''__pycache__/
*.pyc
*.blend
*.blend1
*.usd
*.usda
*.usdc
*.usdz
*.zip
*.exe
*.dll
*.pdb
.env
auth.json
userpref.blend
node_modules/
sources/
artifacts/
blender_profile/
sdk/
''',encoding='utf-8')
    (out/'.gitattributes').write_text('* -text\n',encoding='utf-8')
    write(out/'SOURCE_INVENTORY.json',dict(files=inventory,common_core_commit=subprocess.run(['git','-C',str(workspace/'common_core'),'-c','safe.directory=C:/hotel_room/common_core','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()))
    suspicious=[]
    patterns=[re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(r'github_pat_[A-Za-z0-9_]{30,}'),re.compile(r'AKIA[0-9A-Z]{16}'),re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
    for f in out.rglob('*'):
        if f.is_file():
            text=f.read_text(encoding='utf-8-sig')
            if any(pattern.search(text) for pattern in patterns):suspicious.append(str(f.relative_to(out)))
    assert not suspicious,suspicious
    files=[f for f in out.rglob('*') if f.is_file()]
    write(out/'SNAPSHOT_AUDIT.json',dict(outcome='PASS',files=len(files),bytes=sum(f.stat().st_size for f in files),secret_pattern_hits=suspicious,policy='Explicit code/metadata whitelist; no binary models, textures, runtime profiles, PDF, SDK or credentials. No broad workspace/git add.'))
    print('GITHUB_SNAPSHOT_READY',out,'files',len(files))

if __name__=='__main__':main()
