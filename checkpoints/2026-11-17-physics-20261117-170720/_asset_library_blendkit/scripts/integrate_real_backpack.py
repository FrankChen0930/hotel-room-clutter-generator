"""Independent controlled-local Hotel705 candidate. Never writes formal Core or V0.2 inputs."""
import copy
import dataclasses
import os
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha
import usd_sdk
usd_sdk.load()
CORE=ROOT.parent/'common_core';sys.path.insert(0,str(CORE))
from common_core.contracts import validate_contract
from common_core.room import load_inputs,prepare_room,geometry_signature
from common_core.placer import place_requests
from common_core.writer import write_scene
from common_core.manifest import build_manifest,seal_manifest
from common_core.validation import validate_static,validate_integrity
from common_core.replay import replay_manifest
from common_core.identity import stable_request_id,content_digest
from pxr import Usd,UsdGeom,UsdPhysics,Gf
import common_core.paths as core_paths
# User explicitly requested an independent workline. Retain the same new-output
# and reparse checks, with a process-local output root; formal Core bytes stay intact.
core_paths.RUN_ROOT=ROOT/'runs'

BASE='fa971768-8e7e-49dd-93e5-c225b578899e';AID='bk-'+BASE
REF=ROOT.parent/'_common_core_runs/quality_experiments/scene_quality_v02_20261114T153126Z'

def main(tag='a002',base=BASE,conversion_dir=None,state_id='lying_scan',support_ids=None,replace_request_ids=None):
    AID='bk-'+base
    record=next(x for x in read(ROOT/'registry/assets.json')['assets'] if x['asset_id']==AID)
    category=record['category'];support_ids=support_ids or ['floor_luggage']
    raw=Path(conversion_dir) if conversion_dir else ROOT/'artifacts'/base/'convert_a000'
    qual=ROOT/'artifacts'/base/('qualified_'+tag);qual.mkdir(parents=True,exist_ok=False)
    integrity=read(raw/'integrity.json');dims=integrity['dimensions_m'];bounds=integrity['bounds_m']
    for dep in integrity['dependencies']:
        src=Path(dep['path']);dest=qual/'visual'/src.relative_to(raw)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    asset=qual/'asset.usda';stage=Usd.Stage.CreateNew(str(asset));root=UsdGeom.Xform.Define(stage,'/Asset').GetPrim();stage.SetDefaultPrim(root)
    UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    visual=UsdGeom.Xform.Define(stage,'/Asset/Visual');visual.GetPrim().GetReferences().AddReference('visual/asset.usdc','/Asset')
    body=UsdGeom.Cube.Define(stage,'/Asset/CollisionProxies/Body');body.CreateSizeAttr(1)
    xf=UsdGeom.Xformable(body);xf.AddTranslateOp().Set(Gf.Vec3d(0,0,dims[2]/2));xf.AddScaleOp().Set(Gf.Vec3f(*dims))
    body.CreateVisibilityAttr('invisible');UsdPhysics.CollisionAPI.Apply(body.GetPrim()).CreateCollisionEnabledAttr(True)
    stage.GetRootLayer().Save()
    proxy=dict(kind='box',capability='STATIC_ONLY',shape_paths=['CollisionProxies/Body'],
        geometry_hash=geometry_signature(body.GetPrim()),
        relative_transforms=[[[float(xf.GetLocalTransformation()[i][j]) for j in range(4)] for i in range(4)]],
        mass=dict(mode='NOT_QUALIFIED_STATIC_ONLY',authored_kg=None),inertia=dict(mode='NOT_QUALIFIED_STATIC_ONLY',authored_diagonal=None),
        material_refs=[],provenance=dict(kind='CONSERVATIVE_VISUAL_AABB_PROXY',qualification='Static support/placement only; not dynamic stability or exact contact geometry'))
    write(qual/'proxy.json',dict(outcome='PASS',usd_sha256=sha(asset),proxy=proxy,dimensions_m=dims,
        support_footprint='Conservative XY AABB containing full visual scan, including straps',dynamics='NOT_QUALIFIED'))
    cfgdir=ROOT/('config/local_backpack_'+tag);cfgdir.mkdir(parents=True,exist_ok=False)
    cfg=read(REF/'config/accepted/v4_bed/deployment.json');cfg['bindings']['blendkit_library']=str(ROOT)
    cfg.update(rooms=dict(hotel705='profile.json'),catalog='catalog.json',policy='policy.json',source_lock='source_lock.json')
    profile=read(REF/'config/accepted/v4_bed/profile.json');profile['profile_version']='blendkit-local-'+tag
    policy=read(REF/'config/accepted/v4_bed/policy.json');policy.update(policy_id='blendkit-controlled-local',version='1.0-local-unfrozen',release_frozen=False)
    policy['scenarios']['STAYOVER']['eligible_categories']=sorted(set(policy['scenarios']['STAYOVER']['eligible_categories'])|{category})
    policy['levels']['high']['eligible_categories']=sorted(set(policy['levels']['high']['eligible_categories'])|{category})
    prior_states=policy['levels']['high'].get('allowed_states',{}).get(category)
    if prior_states is None:
        prior_states=[s['state_id'] for e in read(REF/'config/catalog.accepted.json')['entries'] if e['category']==category for s in e['states']]
    policy['levels']['high'].setdefault('allowed_states',{})[category]=sorted(set(prior_states)|{state_id})
    catalog=read(REF/'config/catalog.accepted.json');catalog.update(catalog_id='blendkit-controlled-local-candidate',version='1.0-local-a000')
    template=copy.deepcopy(next(e for e in catalog['entries'] if e['asset_id']=='book'));state=template['states'][0]
    locator=dict(mount='blendkit_library',path=asset.relative_to(ROOT).as_posix())
    footprint=[[bounds[0][0],bounds[0][1]],[bounds[1][0],bounds[0][1]],[bounds[1][0],bounds[1][1]],[bounds[0][0],bounds[1][1]]]
    from inspect_usd import inspect
    closure=inspect(asset);write(qual/'integrity.json',closure)
    if closure['outcome']!='PASS':raise ValueError('QUALIFIED_ASSET_INTEGRITY_FAILED:'+str(closure['errors']))
    dependencies=[dict(mount='blendkit_library',path=Path(x['path']).relative_to(ROOT).as_posix(),sha256=x['sha256'],bytes=Path(x['path']).stat().st_size) for x in closure['dependencies']]
    template.update(asset_id=AID,category=category,origin='external',source_locator=locator,dependency_hashes=dependencies,root_prim='/Asset',dimensions=dims,
        provenance=dict(kind='OFFICIAL_BLENDKIT_USER_DOWNLOADED',asset_base_id=base,author=record['author'],human_confirmed=False),
        license_scope=record['rights']['license']+'; CONTROLLED_LOCAL_TECHNICAL_TEST_ONLY; EXTRACTABLE_GENERATOR_AND_REDISTRIBUTION_UNCLEARED',qualification_refs=[])
    state.update(state_id=state_id,version='1.0',usd_locator_or_native_prim=locator,sha256=sha(asset),visual_bounds=bounds,
        footprint=footprint,support_envelope=dict(clearance_m=.001),allowed_pose_tags=['upright'],acceptance_refs=[],physics_proxy=proxy)
    catalog['entries'].append(template);validate_contract(catalog,'Catalog')
    lock=read(REF/'config/source_lock.accepted.json');lock['assets']+=dependencies
    for name,value in [('deployment.json',cfg),('profile.json',profile),('policy.json',policy),('catalog.json',catalog),('source_lock.json',lock)]:write(cfgdir/name,value)
    inputs=load_inputs(cfgdir/'deployment.json','hotel705');room=prepare_room(inputs.profile,inputs.bindings)
    supports=copy.deepcopy(room.supports)
    from common_core.adapters import footprint_supported
    for sid,support in supports.items():
        if sid.startswith(('floor_','bed_')):
            assert footprint_supported(support,support['allowed_region'],.005)
            support['source_polygon']=support['polygon'];support['polygon']=support['allowed_region']
    room=dataclasses.replace(room,supports=supports)
    reference=next(x for x in read(REF/'cases/final_case_index.json') if x['version']=='v4_bed')
    old=read(reference['manifest']);requests=copy.deepcopy(old['requests'])
    if replace_request_ids:
        assert set(replace_request_ids)<=set(r['request_id'] for r in requests)
        requests=[r for r in requests if r['request_id'] not in replace_request_ids]
    new_request=dict(request_id=stable_request_id('blendkit-local',AID,0),role='personal',category=category,asset_id=AID,
        state_id=state_id,origin='external',source_object_id=None,
        semantic_state=dict(ownership='GUEST',action_policy='DO_NOT_TOUCH',task_role='PERSONAL_ITEM'),
        allowed_support_ids=support_ids,allowed_pose_tags=['upright'],required=True,priority=0)
    # Place a high-value personal object first, then let existing small clutter
    # use the same deterministic sampler and permitted supports around it.
    requests.insert(0,new_request)
    targets=copy.deepcopy(old['targets']);targets['count']=len(requests)
    targets['count_range']=[min(targets['count_range'][0],len(requests)),max(targets['count_range'][1],len(requests))]
    targets['required_categories']=sorted(set(targets['required_categories'])|{category})
    if replace_request_ids:
        targets['required_categories']=[c for c in targets['required_categories'] if any(r['category']==c for r in requests)]
        targets['required_state_counts']={key:min(count,sum(r['asset_id']+'/'+r['state_id']==key for r in requests)) for key,count in targets.get('required_state_counts',{}).items() if any(r['asset_id']+'/'+r['state_id']==key for r in requests)}
    plan=dict(seed=706,scenario='STAYOVER',level='high',requests=requests,targets=targets,budgets=copy.deepcopy(inputs.policy['budgets']),
        assumptions=['CONTROLLED_LOCAL_TECHNICAL_TEST_ONLY','V02_LOCAL_FLOOR_REGIONS','ONE_REAL_BLENDKIT_ASSET','NO_DYNAMIC_QUALIFICATION'])
    run=ROOT/('runs/real_backpack_hotel705_stayover_high_706_'+tag);run.mkdir(parents=True,exist_ok=False);write(run/'request.json',plan)
    if replace_request_ids:write(run/'replacement_policy.json',dict(replaced_request_ids=replace_request_ids,reason='Activity-based independent candidate substitution to avoid occupied local support; no manual poses'))
    selected=None
    for ordinal in range(3):
        attempt=run/'attempts'/f'a{ordinal:03d}';attempt.mkdir(parents=True)
        placements=place_requests(plan,room,inputs.catalog,attempt_ordinal=ordinal);write(attempt/'placement.json',placements)
        if placements['status']!='PASS':continue
        scene=attempt/'scene.usda';write_scene(scene,inputs,placements)
        manifest=build_manifest(inputs,plan,placements,scene,run.name,attempt_id=attempt.name)
        static=validate_static(scene,manifest,room,inputs);full_integrity=validate_integrity(inputs,manifest)
        write(attempt/'static.json',static);write(attempt/'integrity.json',full_integrity)
        if static['outcome']!='PASS' or full_integrity['outcome']!='PASS':
            write(attempt/'failed_manifest.json',manifest);continue
        replay=replay_manifest(manifest,attempt/'replay',inputs,scene);write(attempt/'replay.json',replay)
        manifest['achieved']=static['metrics']
        for kind,report in [('static',static),('integrity',full_integrity),('replay',replay)]:
            manifest['evidence_refs'].append(dict(kind=kind,uri=kind+'.json',sha256=sha(attempt/(kind+'.json')),
                execution='EXECUTED',outcome=report['outcome'],scope=report['scope'],target_state_digest=manifest['scene']['state_digest'],producer_identity=dict(code_hash=manifest['inputs']['code_hash'])))
        manifest['limits']+=['Controlled local-only RF technical test; generator/public rights not cleared','Native support and scene rendering pending',
            'Process-local Common Core output root: '+str(core_paths.RUN_ROOT)]
        seal_manifest(manifest,attempt/'manifest.json');selected=attempt;break
    if not selected:raise ValueError('BOUNDED_CANDIDATE_PLACEMENT_OR_STATIC_FAILED; inspect run attempts')
    index=dict(outcome='STATIC_INTEGRITY_REPLAY_EXECUTED',config=str(cfgdir/'deployment.json'),manifest=str(selected/'manifest.json'),scene=str(selected/'scene.usda'),
        count=len(requests),asset_id=AID,asset_sha256=sha(asset),asset=str(asset),scope='Independent controlled-local High candidate; not public/generator-qualified')
    index['producer_script_sha256']=sha(__file__)
    write(run/'case_index.json',index)
    write(run/'support_batch.json',dict(cases=[dict(room='hotel705',manifest=str(selected/'manifest.json'),config=str(cfgdir/'deployment.json'))]))
    camera_reference=next(x for x in read(REF/'comparison_index.json')['cases'] if x['version']=='v4_bed')
    write(run/'render_batch.json',dict(cases=[dict(manifest=str(selected/'manifest.json'),cameras={x['view']:x['camera'] for x in camera_reference['images'] if x['view'] in ('overview','floor_foot')})]))
    print('REAL_BACKPACK_CANDIDATE_STATIC_REPLAY',str(selected),len(requests))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--tag',default='a002');p.add_argument('--base-id',default=BASE)
    p.add_argument('--conversion-dir',type=Path);p.add_argument('--state',default='lying_scan');p.add_argument('--supports',nargs='+')
    p.add_argument('--replace-request-ids',nargs='+');a=p.parse_args();main(a.tag,a.base_id,a.conversion_dir,a.state,a.supports,a.replace_request_ids)
