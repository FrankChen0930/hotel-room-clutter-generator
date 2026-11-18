"""Recomputed exact-case qualifications; never an asset-wide capability flag."""
from pathlib import Path
from .contracts import load_json
from .identity import content_digest, sha256_file
from .replay import load_manifest
from .room import geometry_signature, prepare_room
from .runtime import runtime_environment
from .writer import object_prim


def require(condition, reason):
    if not condition: raise ValueError('QUALIFICATION_' + reason)


def assess(case_dir, inputs, visual_review=None):
    from pxr import Usd, UsdGeom
    directory = Path(case_dir).resolve(strict=True)
    case, claim, result, process = [load_json(directory/name) for name in
        ['case.json', 'dispatch_claim.json', 'result.json', 'process.json']]
    require(content_digest(case) == claim['case_hash'], 'CASE_HASH')
    require(case.get('purpose') in ['EXACT_FIXTURE', 'RELEASE_REPRESENTATIVE'], 'PURPOSE')
    require(process['native_exit_code'] == 0 and process['termination_reason'] is None and process['outcome'] == 'PASS', 'PROCESS')
    require(result['execution'] == 'EXECUTED' and result['outcome'] == 'PASS', 'RESULT')
    require(result['checks'] and all(v is True for v in result['checks'].values()), 'CHECKS')
    require(result['target_checks'] and all(v is True for checks in result['target_checks'].values() for v in checks.values()), 'TARGET_CHECKS')
    require(result['native_steps'] == 240 and len(result['native_dt']) == 240 and
            all(abs(dt-1/120) < 1e-8 for dt in result['native_dt']), 'STEPS')
    require(case['physics'] == dict(steps=240, hz=120, device='cpu', fabric=False), 'PHYSICS')
    require(not result['callback_errors'] and not result['physx_errors'] and result['source_saved'] is False, 'NATIVE_ERRORS')
    runtime = runtime_environment()
    require(case.get('runtime_fingerprint') == runtime, 'RUNTIME')
    require(runtime['gpu']['outcome'] == 'PASS' and runtime['physics_binary_hashes'], 'RUNTIME_INCOMPLETE')
    worker = Path(__file__).with_name('native_validation.py')
    require(result['worker_sha256'] == sha256_file(worker), 'WORKER')
    require(result['runtime_version'] == runtime['isaac_build'], 'BUILD')
    manifest_path = Path(case['manifest']).resolve(strict=True)
    manifest = load_manifest(manifest_path, inputs)
    scene = Path(case['scene']).resolve(strict=True)
    require(scene == manifest_path.parent/'scene.usda', 'SCENE_PATH')
    require(sha256_file(manifest_path) == case['manifest_sha256'] == result['manifest_sha256'], 'MANIFEST')
    require(sha256_file(scene) == case['scene_sha256'] == result['scene_sha256'], 'SCENE')
    require(manifest['scene']['state_digest'] == case['state_digest'] == result['target_state_digest'], 'STATE')
    require(case['source_closure_hash'] == inputs.profile['source']['closure_sha256'], 'SOURCE')
    refs = {ref['kind']: ref for ref in manifest['evidence_refs']}
    for kind in ['static', 'integrity', 'replay']:
        require(kind in refs and refs[kind]['execution'] == 'EXECUTED' and refs[kind]['outcome'] == 'PASS', kind.upper())
        report = load_json(manifest_path.parent/refs[kind]['uri'])
        require(report['execution'] == 'EXECUTED' and report['outcome'] == 'PASS', kind.upper()+'_REPORT')
    stage = Usd.Stage.Open(str(scene)); room = prepare_room(inputs.profile, inputs.bindings)
    require(case['targets'] and len({t['instance_id'] for t in case['targets']}) == len(case['targets']), 'TARGETS')
    identities = []
    for target in case['targets']:
        obj = next(o for o in manifest['objects'] if o['instance_id'] == target['instance_id'])
        entry = next(e for e in inputs.catalog['entries'] if e['asset_id'] == obj['asset_id'])
        state = next(s for s in entry['states'] if s['state_id'] == obj['effective']['state_id'])
        proxy = state['physics_proxy']; root = object_prim(obj)
        require(state['sha256'] == obj['state_sha256'], 'ASSET_STATE')
        require(proxy['capability'] == 'DYNAMIC_CANDIDATE' and proxy['kind'] == target['proxy_kind'], 'CAPABILITY')
        require(target['prim'] == root and target['shape'] in [root+'/'+p for p in proxy['shape_paths']], 'COLLIDER_PATH')
        shape = stage.GetPrimAtPath(target['shape'])
        require(shape and geometry_signature(shape) == target['proxy_geometry_hash'], 'COLLIDER')
        matrix = [[float(v) for v in row] for row in UsdGeom.Xformable(stage.GetPrimAtPath(root)).ComputeLocalToWorldTransform(0)]
        require(matrix == obj['effective']['world_matrix'] == target['initial_world_matrix'], 'POSE')
        support_id = obj['effective']['support_id']; spec = next(s for s in inputs.profile['supports'] if s['support_id'] == support_id)
        require(content_digest(target['support']) == content_digest(room.supports[support_id]) and target['support_collider'] == spec['collider'], 'SUPPORT')
        require(root in result['target_checks'] and root in result['physical_properties'], 'TARGET_REPORT')
        identities.append(dict(object=obj, proxy=proxy, support=target,
            support_geometry_hash=geometry_signature(stage.GetPrimAtPath(spec['collider'])), physical_properties=result['physical_properties'][root]))
    if case['purpose'] == 'RELEASE_REPRESENTATIVE':
        require(visual_review is not None,'VISUAL')
        from .visual import verify_review
        visual_identity=verify_review(visual_review,manifest_path)
    identity=dict(schema='ExactQualification/1', scope='Named targets, exact scene and runtime only; no asset-wide or cloth qualification',
        case_directory=str(directory), purpose=case['purpose'], inputs=manifest['inputs'], manifest_sha256=sha256_file(manifest_path),
        scene_sha256=sha256_file(scene), state_digest=case['state_digest'], targets=identities, runtime=runtime,
        physics=case['physics'], worker_sha256=sha256_file(worker),
        evidence={name:sha256_file(directory/name) for name in ['case.json','dispatch_claim.json','result.json','process.json','process.log']})
    if case['purpose']=='RELEASE_REPRESENTATIVE':identity['visual_review']=visual_identity
    return identity


def qualify(case_dir, inputs, visual_review=None):
    identity = assess(case_dir, inputs, visual_review)
    return dict(execution='EXECUTED', outcome='PASS', identity=identity, fingerprint=content_digest(identity))


def verify(record, inputs):
    require(record.get('execution') == 'EXECUTED' and record.get('outcome') == 'PASS', 'RECORD')
    require(content_digest(record['identity']) == record['fingerprint'], 'FINGERPRINT')
    visual=record['identity'].get('visual_review',{}).get('path')
    require(qualify(record['identity']['case_directory'], inputs,visual) == record, 'STALE')
    return True
