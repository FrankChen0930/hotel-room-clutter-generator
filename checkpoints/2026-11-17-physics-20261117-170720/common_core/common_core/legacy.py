"""Explicit read-only importer for the adopted Hotel schema-2 roomscale fixtures."""
from copy import deepcopy
import json
from pathlib import Path
from .contracts import load_json,verify_source
from .identity import sha256_file
from .manifest import write_json_new
from .paths import guard_new_output
from .replay import signatures
from .room import Inputs
from .writer import object_prim,write_scene


def import_hotel_v2(manifest_path,output,inputs):
    from pxr import Usd,UsdGeom
    manifest_path=Path(manifest_path).resolve(strict=True);old=load_json(manifest_path)
    if old.get('schema_version')!=2:raise ValueError('LEGACY_SCHEMA_UNSUPPORTED')
    verify_source(Path(old['source_path']),old['source_sha256'])
    for record in old['dependencies']:verify_source(Path(record['path']),record['sha256'])
    before=sha256_file(manifest_path);old_scene=manifest_path.parent/'scene.usda';scene_before=sha256_file(old_scene)
    profile=deepcopy(inputs.profile);catalog=deepcopy(inputs.catalog);entries={e['asset_id']:e for e in catalog['entries']}
    objects=[];paths={};expected_semantics={}
    mounts={key:Path(value).resolve() for key,value in inputs.bindings.items()}
    for item in old['objects']:
        native=item['origin']=='SOURCE_AMENITY';asset_id='legacy_'+item['id'].lower()
        if native:
            asset_id=next(e['asset_id'] for e in catalog['entries'] if e['origin']=='native' and e['source_locator']==item['prim'])
            for entry in profile['override_allowlist']:
                if entry['prim']==item['prim'] and 'physics:mass' not in entry['attributes']:entry['attributes'].append('physics:mass')
        else:
            path=Path(item['asset_path']).resolve();matches=[(key,root) for key,root in mounts.items() if path.is_relative_to(root)]
            if not matches:raise ValueError('LEGACY_ASSET_MOUNT_UNDECLARED')
            key,root=matches[0];asset_stage=Usd.Stage.Open(str(path));default=asset_stage.GetDefaultPrim()
            catalog['entries'].append(dict(asset_id=asset_id,origin='external',source_locator=dict(mount=key,path=path.relative_to(root).as_posix()),root_prim=str(default.GetPath())))
        effective=dict(world_matrix=item['world_matrix'],state_id=item['state'],support_id=item['support'],
                       semantic_state=item['semantics'],body_mode='kinematic',mass_kg=item['mass_kg_estimated'])
        obj=dict(instance_id='legacy/'+item['id'],request_id='legacy/'+item['id'],asset_id=asset_id,
                 origin='native' if native else 'external',native_prim=item['prim'] if native else None,effective=effective)
        objects.append(obj);paths[obj['instance_id']]=item['prim'];expected_semantics[obj['instance_id']]=item['semantics']
    adapted=Inputs(profile,catalog,inputs.policy,inputs.bindings,inputs.source_lock)
    output=guard_new_output(output);output.mkdir(parents=True);stage=write_scene(output/'scene.usda',adapted,dict(objects=objects))
    original=Usd.Stage.Open(str(old_scene));actual=signatures(stage,objects,ignore_semantic_namespace=True)
    expected=signatures(original,objects,path_overrides=paths,ignore_semantic_namespace=True);errors=[];max_error=0.
    for obj in objects:
        key=obj['instance_id'];a=actual[key];b=expected[key]
        delta=max(abs(a['matrix'][i][j]-b['matrix'][i][j]) for i in range(4) for j in range(4));max_error=max(max_error,delta)
        if delta>1e-8:errors.append('LEGACY_MATRIX_MISMATCH: '+key)
        if a['content']!=b['content']:errors.append('LEGACY_GEOMETRY_MATERIAL_BODY_MISMATCH: '+key)
        current=json.loads(stage.GetPrimAtPath(object_prim(obj)).GetAttribute('commoncore:semantics').Get())
        old_prim=original.GetPrimAtPath(paths[key]);prior={k:old_prim.GetAttribute('clutter:'+k).Get() for k in expected_semantics[key]}
        if current!=prior:errors.append('LEGACY_SEMANTICS_MISMATCH: '+key)
    if before!=sha256_file(manifest_path) or scene_before!=sha256_file(old_scene):raise ValueError('LEGACY_SOURCE_MODIFIED')
    result=dict(execution='EXECUTED',outcome='FAIL' if errors else 'PASS',legacy_manifest_sha256=before,legacy_scene_sha256=scene_before,
                scene_sha256=sha256_file(output/'scene.usda'),max_matrix_error=max_error,objects=len(objects),errors=errors,
                scope='explicit schema2 effective-pose import; normalized object geometry/material/body state and semantics; no historical validators executed')
    write_json_new(output/'legacy_replay.json',result);return result
