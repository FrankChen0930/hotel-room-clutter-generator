"""Manifest replay without planner, placer or RNG calls."""
from copy import deepcopy
from pathlib import Path
from .contracts import load_json,validate_contract
from .identity import content_digest,sha256_file,state_digest
from .manifest import write_json_new
from .paths import guard_new_output
from .writer import object_prim,write_scene


def load_manifest(path,inputs):
    path=Path(path).resolve(strict=True);manifest=validate_contract(load_json(path),'Manifest')
    if manifest['scene']['state_digest']!=state_digest(manifest):raise ValueError('STATE_DIGEST_MISMATCH')
    for key,value in [('profile_hash',inputs.profile),('catalog_hash',inputs.catalog),('policy_hash',inputs.policy)]:
        if manifest['inputs'][key]!=content_digest(value):raise ValueError('INPUT_IDENTITY_MISMATCH: '+key)
    if manifest['inputs']['source_closure_hash']!=inputs.profile['source']['closure_sha256']:
        raise ValueError('SOURCE_CLOSURE_IDENTITY')
    for ref in manifest['evidence_refs']:
        relative=Path(ref['uri'])
        evidence=(path.parent/relative).resolve(strict=True)
        if relative.is_absolute() or not evidence.is_relative_to(path.parent):raise ValueError('EVIDENCE_PATH_ESCAPE')
        if sha256_file(evidence)!=ref['sha256']:raise ValueError('EVIDENCE_HASH_MISMATCH')
        if ref['target_state_digest']!=manifest['scene']['state_digest']:raise ValueError('EVIDENCE_STATE_MISMATCH')
    scene=path.parent/'scene.usda'
    if scene.exists() and sha256_file(scene)!=manifest['scene']['sha256']:raise ValueError('SCENE_HASH_MISMATCH')
    return manifest


def signatures(stage,objects,path_overrides=None,ignore_semantic_namespace=False):
    from pxr import Usd,UsdGeom
    result={}
    for obj in objects:
        path=(path_overrides or {}).get(obj['instance_id'],object_prim(obj));root=stage.GetPrimAtPath(path)
        if not root:raise ValueError('REPLAY_PRIM_MISSING')
        records=[]
        for prim in Usd.PrimRange(root,Usd.TraverseInstanceProxies()):
            attrs={a.GetName():str(a.Get()) for a in prim.GetAttributes()
                   if not a.GetName().startswith('xformOp') and not (ignore_semantic_namespace and a.GetName().startswith(('commoncore:','clutter:')))}
            relations={r.GetName():[str(t).replace(path,'/OBJECT',1) for t in r.GetTargets()] for r in prim.GetRelationships()}
            records.append(dict(path=str(prim.GetPath()).replace(path,'/OBJECT',1),type=prim.GetTypeName(),
                                attrs=attrs,relations=relations))
        matrix=UsdGeom.Xformable(root).ComputeLocalToWorldTransform(0)
        result[obj['instance_id']]=dict(content=content_digest(records),matrix=[[float(matrix[i][j]) for j in range(4)] for i in range(4)])
    return result


def replay_manifest(manifest,output,inputs,original_scene=None,manifest_sha256=None):
    from pxr import Usd,UsdUtils
    output=guard_new_output(output);output.mkdir(parents=True,exist_ok=False)
    scene=output/'scene.usda';stage=write_scene(scene,inputs,dict(objects=manifest['objects']))
    actual=signatures(stage,manifest['objects']);errors=[];max_error=0.
    for obj in manifest['objects']:
        matrix=actual[obj['instance_id']]['matrix'];expected=obj['effective']['world_matrix']
        error=max(abs(matrix[i][j]-expected[i][j]) for i in range(4) for j in range(4));max_error=max(max_error,error)
        if error>1e-8:errors.append('REPLAY_MATRIX_MISMATCH: '+obj['instance_id'])
    if original_scene is not None:
        original=Usd.Stage.Open(str(original_scene));expected=signatures(original,manifest['objects'])
        for key,value in expected.items():
            if actual[key]['content']!=value['content']:errors.append('REPLAY_GEOMETRY_SEMANTICS_MATERIAL_MISMATCH: '+key)
    unresolved=UsdUtils.ComputeAllDependencies(str(scene))[2]
    if unresolved:errors.append('REPLAY_DEPENDENCY_UNRESOLVED')
    report=dict(execution='EXECUTED',outcome='FAIL' if errors else 'PASS',target_state_digest=state_digest(manifest),
        authoritative_manifest_sha256=manifest_sha256,scene_sha256=sha256_file(scene),max_matrix_error=max_error,
        rng_calls=0,scope='effective matrices, geometry/semantics/materials when original available, dependency composition; no sampling or native physics',
        original_compared=original_scene is not None,errors=errors)
    write_json_new(output/'replay.json',report)
    return report
