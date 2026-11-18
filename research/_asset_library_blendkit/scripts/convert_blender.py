"""Offline converter. Run in factory-startup Blender, -- JOB.json. Originals are never saved."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback
import bpy
from mathutils import Matrix, Vector

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def convert(job, out):
    source=Path(job['blend']).resolve(strict=True)
    if digest(source)!=job['source_sha256']: raise ValueError('SOURCE_SHA_MISMATCH')
    if job.get('internal_conversion_authorized') is not True: raise ValueError('INTERNAL_RIGHTS_REQUIRED')
    # Load without executing scripts, including file-saved auto-run settings.
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    collection=bpy.data.collections.get(job['collection'])
    if collection is None: raise ValueError('EXACT_ASSET_COLLECTION_REQUIRED')
    meshes=[o for o in collection.all_objects if o.type=='MESH' and not o.hide_render]
    if not meshes: raise ValueError('NO_RENDERABLE_MESH')
    if any(o.type=='CURVES' or o.instance_type!='NONE' for o in collection.all_objects):
        raise ValueError('INSTANCES_OR_HAIR_REQUIRE_EXPLICIT_REALIZATION')
    unit=bpy.context.scene.unit_settings.scale_length
    if not 0 < unit <= 1000: raise ValueError('INVALID_SOURCE_UNITS')
    deps=bpy.context.evaluated_depsgraph_get(); copies=[]; material_issues=[]; source_images=[]
    for obj in meshes:
        evaluated=obj.evaluated_get(deps)
        mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
        mesh.transform(Matrix.Scale(unit,4) @ obj.matrix_world)
        if not mesh.vertices or not mesh.polygons: raise ValueError('EMPTY_MESH:'+obj.name)
        copies.append((obj.name,mesh))
        if not mesh.materials or any(m is None for m in mesh.materials): material_issues.append(obj.name+':missing_material')
        for m in mesh.materials:
            if m is None or not m.use_nodes: continue
            # Fail closed for procedural networks requiring baking, rather than exporting flat placeholders.
            supported={'OUTPUT_MATERIAL','BSDF_PRINCIPLED','TEX_IMAGE','NORMAL_MAP','UVMAP','TEX_COORD','MAPPING','REROUTE'}
            for n in m.node_tree.nodes:
                if n.type not in supported and any(s.is_linked for s in n.outputs):
                    material_issues.append(m.name+':requires_bake:'+n.type)
                if n.type=='TEX_IMAGE' and any(s.is_linked for s in n.outputs):
                    im=n.image
                    if im is None: material_issues.append(m.name+':missing_image'); continue
                    if im.source in {'TILED','SEQUENCE','MOVIE','GENERATED','VIEWER'}:
                        material_issues.append(m.name+':unsupported_image_source:'+im.source)
                    p=Path(bpy.path.abspath(im.filepath,library=im.library))
                    packed=bool(im.packed_file)
                    source_images.append(dict(name=im.name,packed=packed,exists=p.is_file(),
                        source_sha256=digest(p) if p.is_file() else None))
                    if not packed and not p.is_file(): material_issues.append(m.name+':missing_texture:'+im.name)
                    if len(mesh.uv_layers)==0: material_issues.append(obj.name+':textured_mesh_missing_uv')
    vertices=[v.co.copy() for _,mesh in copies for v in mesh.vertices]
    lo=Vector(tuple(min(v[i] for v in vertices) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in vertices) for i in range(3)))
    dim=hi-lo
    bounds=job['dimension_bounds_m']
    if any(not bounds['min'][i]<=dim[i]<=bounds['max'][i] for i in range(3)):
        raise ValueError('DIMENSIONS_OUT_OF_CATEGORY_BOUNDS:'+str(list(dim)))
    offset=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
    scene=bpy.data.scenes.new('AssetLibraryConversion'); bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    identity=[]
    for name,mesh in copies:
        mesh.transform(Matrix.Translation(offset))
        ob=bpy.data.objects.new(name,mesh); scene.collection.objects.link(ob)
        identity.append(dict(vertices=[[round(float(x),7) for x in v.co] for v in mesh.vertices],
            faces=[list(p.vertices) for p in mesh.polygons]))
    report=dict(outcome='BLOCKED' if material_issues else 'PASS',source_sha256=job['source_sha256'],
        blender_version=bpy.app.version_string,source_collection=job['collection'],
        dimensions_m=list(dim),source_unit_scale=unit,normalization_translation_m=list(offset),
        geometry_identity=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
        geometry_identity_scope='Normalized evaluated topology fingerprint; cross-topology/permutation duplicates still require manual review',
        mesh_count=len(copies),polygons=sum(len(m.polygons) for _,m in copies),
        uv_layers={name:len(m.uv_layers) for name,m in copies},images=source_images,
        blockers=sorted(set(material_issues)),physics_mode='STATIC_ONLY',state_id=job.get('state_id','default'),
        scope=job.get('scope','REAL_ASSET_CONVERSION_PENDING_NATIVE_REVIEW'))
    if material_issues: return report
    export=out/'asset.usdc'
    result=bpy.ops.wm.usd_export(filepath=str(export),root_prim_path='/Asset',
        export_materials=True,export_uvmaps=True,export_normals=True,
        export_textures_mode='NEW',overwrite_textures=False,generate_preview_surface=True,
        relative_paths=True,convert_scene_units='METERS',export_cameras=False,export_lights=False)
    if 'FINISHED' not in result or not export.is_file(): raise RuntimeError('EXPORT_FAILED')
    report['usd_sha256']=digest(export)
    report['outputs']=[dict(path=str(p.relative_to(out)),sha256=digest(p)) for p in out.rglob('*') if p.is_file()]
    if digest(source)!=job['source_sha256']: raise RuntimeError('ORIGINAL_CHANGED')
    return report

def main():
    args=sys.argv[sys.argv.index('--')+1:]; job=json.loads(Path(args[0]).read_text(encoding='utf-8-sig'))
    out=Path(job['output']).resolve(); out.mkdir(parents=True,exist_ok=False)
    try: report=convert(job,out)
    except Exception:
        report=dict(outcome='FAIL',reason=traceback.format_exc(),scope=job.get('scope'))
    (out/'conversion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CONVERSION',report['outcome'],str(out))
    if report['outcome']!='PASS': raise RuntimeError('CONVERSION_NOT_PASS; see conversion.json')

if __name__=='__main__':main()
