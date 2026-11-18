"""One effective-state authority and immutable JSON evidence references."""
from copy import deepcopy
from pathlib import Path
import platform
import sys
from .contracts import validate_contract
from .identity import content_digest,sha256_file,state_digest


def write_json_new(path,data):
    import json
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def code_identity():
    root=Path(__file__).resolve().parents[1]
    files={p.relative_to(root).as_posix():sha256_file(p) for p in sorted((root/'common_core').glob('*.py'))}
    return content_digest(files)


def build_manifest(inputs,plan,placements,scene,run_id,attempt_id='a000'):
    from .runtime import runtime_environment
    categories={e['asset_id']:e['category'] for e in inputs.catalog['entries']};category_counts={};state_counts={}
    for obj in placements['objects']:
        category=categories[obj['asset_id']];category_counts[category]=category_counts.get(category,0)+1
        key=obj['asset_id']+'/'+obj['effective']['state_id'];state_counts[key]=state_counts.get(key,0)+1
    manifest=dict(schema_version='3.0',generator_version='1.0',run_id=run_id,attempt_id=attempt_id,parent_attempt_id=None,
        inputs=dict(code_hash=code_identity(),profile_hash=content_digest(inputs.profile),catalog_hash=content_digest(inputs.catalog),
            policy_hash=content_digest(inputs.policy),source_closure_hash=inputs.profile['source']['closure_sha256'],
            seed=plan['seed'],scenario=plan['scenario'],level=plan['level']),
        environment=dict(**runtime_environment(),scope='USD static only; physics/render NOT_RUN'),
        requests=deepcopy(plan['requests']),targets=deepcopy(plan['targets']),
        achieved=dict(count=len(placements['objects']),category_counts=category_counts,state_counts=state_counts),objects=deepcopy(placements['objects']),
        scene=dict(locator=dict(mount='run',path='attempts/'+attempt_id+'/scene.usda'),sha256=sha256_file(scene),state_digest='0'*64,dependencies=[]),
        evidence_refs=[],failure_refs=[],attempt_lineage=[],limits=['Support query NOT_RUN','Visual NOT_RUN','Dynamic physics NOT_RUN'])
    if not inputs.policy.get('release_frozen'):manifest['limits'].append('UNFROZEN_POLICY: release coverage acceptance not claimed')
    manifest['scene']['state_digest']=state_digest(manifest)
    validate_contract(manifest,'Manifest')
    return manifest


def seal_manifest(manifest,output):
    validate_contract(manifest,'Manifest')
    if state_digest(manifest)!=manifest['scene']['state_digest']:raise ValueError('STATE_DIGEST_MISMATCH')
    parent=Path(output).parent.resolve()
    for ref in manifest['evidence_refs']:
        path=(parent/ref['uri']).resolve(strict=True)
        if not path.is_relative_to(parent):raise ValueError('EVIDENCE_PATH_ESCAPE')
        if sha256_file(path)!=ref['sha256'] or ref['target_state_digest']!=manifest['scene']['state_digest']:
            raise ValueError('EVIDENCE_IDENTITY_MISMATCH')
    write_json_new(output,manifest)
