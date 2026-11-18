"""Freeze explicitly selected real-source meshes; bake only unsupported Base Color graphs."""
import bpy
import math
from mathutils import Euler
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha
from bake_channel import bake_channel
from source_surface import prune_constant_surface,canonicalize_simple_surface
from bump_surface import translate_bump_only

def prepare(job):
    source=ROOT/job['source']['path'];before=sha(source)
    if before!=job['source']['sha256']:raise ValueError('SOURCE_SHA_MISMATCH')
    out=ROOT/job['prepare_dir'];out.mkdir(parents=True,exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    source_unit=bpy.context.scene.unit_settings.scale_length;frame=bpy.context.scene.frame_current
    deps=bpy.context.evaluated_depsgraph_get();frozen=[]
    for name in job['meshes']:
        obj=bpy.data.objects.get(name)
        if obj is None or obj.type!='MESH':raise ValueError('EXACT_SOURCE_MESH_REQUIRED:'+name)
        evaluated=obj.evaluated_get(deps)
        mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
        frozen.append((name,mesh,evaluated.matrix_world.copy()))
    scene=bpy.data.scenes.new('Prepared_'+job['base_id'][:8]);bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=source_unit
    col=bpy.data.collections.new('PreparedSource');scene.collection.children.link(col)
    objects=[];bakes=[];texture_reductions=[];image_copies={};texture_locator_repairs=[];surface_pruning=[];generated_bake_uvs=[]
    rotation=Euler(tuple(math.radians(v) for v in job.get('source_root_rotation_deg',[0,0,0])),'XYZ').to_matrix().to_4x4()
    for name,mesh,matrix in frozen:
        obj=bpy.data.objects.new(name,mesh);obj.matrix_world=rotation@matrix;col.objects.link(obj);objects.append(obj)
    for obj in objects:
        mesh=obj.data
        if not mesh.uv_layers and job.get('allow_generated_bake_uv'):
            for item in scene.objects:item.select_set(False)
            obj.select_set(True);bpy.context.view_layer.objects.active=obj
            counts=(len(mesh.vertices),len(mesh.polygons))
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02)
            bpy.ops.object.mode_set(mode='OBJECT')
            assert counts==(len(mesh.vertices),len(mesh.polygons)) and mesh.uv_layers
            generated_bake_uvs.append(dict(mesh=obj.name,method='Blender Smart UV Project',
                reason='Explicit derivative bake atlas for procedural source with no UV; topology and original bytes retained'))
        for index,material in enumerate(list(mesh.materials)):
            if material is None:raise ValueError('MISSING_SOURCE_MATERIAL')
            material=material.copy();mesh.materials[index]=material
            if not material.use_nodes:continue
            surface_pruning.extend(prune_constant_surface(material))
            if job.get('allow_simple_surface_recipes'):
                surface_pruning.extend(canonicalize_simple_surface(material))
            nodes=material.node_tree.nodes;links=material.node_tree.links
            limit=job.get('max_texture_dimension',2048)
            for node in nodes:
                if node.type!='TEX_IMAGE' or node.image is None:continue
                image=node.image
                if image.source=='FILE' and not image.packed_file:
                    path=Path(bpy.path.abspath(image.filepath,library=image.library))
                    if not path.is_file():raise ValueError('MISSING_SOURCE_TEXTURE_BEFORE_BAKE:'+image.name)
                if image.source=='FILE' and min(image.size)<=0:
                    raise ValueError('INVALID_SOURCE_TEXTURE_PIXELS:'+image.name)
            for node in nodes:
                if node.type!='TEX_IMAGE' or node.image is None:continue
                original_image=node.image
                if max(original_image.size)<=limit:continue
                key=original_image.name
                if key not in image_copies:
                    im=original_image.copy();old=list(im.size);scale=limit/max(old)
                    im.scale(max(1,round(old[0]*scale)),max(1,round(old[1]*scale)))
                    # Image.copy retains the source packed blob. Remove that blob
                    # after scaling so repacking uses the derivative pixels.
                    if im.packed_file:im.unpack(method='REMOVE')
                    texture_dir=out/'textures_source';texture_dir.mkdir(exist_ok=True)
                    im.filepath_raw=str(texture_dir/(str(len(image_copies))+'.png'));im.file_format='PNG';im.save();im.pack()
                    image_copies[key]=im
                    texture_reductions.append(dict(source_name=key,original_pixels=old,derivative_pixels=list(im.size),colorspace=im.colorspace_settings.name,
                        reason='Room-scale working derivative; full original is retained byte-for-byte'))
                node.image=image_copies[key]
            # RTX selects its image decoder by suffix. Preserve packed bytes
            # while giving extensionless source textures a verifiable locator.
            for node in nodes:
                if node.type!='TEX_IMAGE' or node.image is None:continue
                image=node.image
                if image.source!='FILE' or Path(image.filepath).suffix or not image.packed_file:continue
                key='extension:'+image.name
                if key not in image_copies:
                    payload=bytes(image.packed_file.data)
                    suffix='.jpg' if payload.startswith(b'\xff\xd8\xff') else '.png' if payload.startswith(b'\x89PNG\r\n\x1a\n') else None
                    if suffix is None:raise ValueError('UNKNOWN_PACKED_TEXTURE_FORMAT:'+image.name)
                    directory=out/'textures_source';directory.mkdir(exist_ok=True)
                    path=directory/('source_'+str(len(image_copies))+suffix);path.write_bytes(payload)
                    copy=image.copy()
                    if copy.packed_file:copy.unpack(method='REMOVE')
                    copy.filepath_raw=str(path);copy.reload();copy.pack()
                    if bytes(copy.packed_file.data)!=payload:raise ValueError('PACKED_TEXTURE_BYTES_CHANGED:'+image.name)
                    image_copies[key]=copy
                    texture_locator_repairs.append(dict(source_image=image.name,path=str(path.relative_to(ROOT)),sha256=sha(path),pixel_bytes_unchanged=True))
                node.image=image_copies[key]
            bsdfs=[n for n in nodes if n.type=='BSDF_PRINCIPLED'];outputs=[n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
            if len(bsdfs)!=1 or len(outputs)!=1:raise ValueError('COMPLEX_SHADER_REQUIRES_RECIPE')
            bsdf=bsdfs[0];output=outputs[0]
            bump_changes=[]
            if output.inputs['Displacement'].is_linked and job.get('allow_bump_only_normal_bake'):
                bump_changes=translate_bump_only(material,obj);surface_pruning.extend(bump_changes)
                if bump_changes:surface_pruning.extend(prune_constant_surface(material))
            if output.inputs['Displacement'].is_linked:raise ValueError('MATERIAL_DISPLACEMENT_REQUIRES_EXPLICIT_GEOMETRY_RECIPE')
            if output.inputs['Volume'].is_linked:raise ValueError('MATERIAL_VOLUME_REQUIRES_EXPLICIT_NATIVE_SHADER_RECIPE')
            supported={'OUTPUT_MATERIAL','BSDF_PRINCIPLED','TEX_IMAGE','NORMAL_MAP','UVMAP','TEX_COORD','MAPPING','REROUTE'}
            def upstream(socket,seen=None):
                seen=set() if seen is None else seen
                for link in socket.links:
                    node=link.from_node
                    if node.name in seen:continue
                    seen.add(node.name)
                    for inp in node.inputs:upstream(inp,seen)
                return seen
            bad=[n for n in nodes if n.type not in supported and any(s.is_linked for s in n.outputs)]
            base_graph=upstream(bsdf.inputs['Base Color'])
            bake_sockets=[]
            if bad:
                covered=set()
                for socket_name in ('Base Color','Roughness','Metallic','Alpha','Normal','Emission Color'):
                    if socket_name not in bsdf.inputs:continue
                    graph=upstream(bsdf.inputs[socket_name]);found={n.name for n in bad if n.name in graph}
                    if found:bake_sockets.append(socket_name);covered|=found
                if not job.get('allow_base_color_bake') or covered!={n.name for n in bad}:
                    raise ValueError('UNSUPPORTED_SHADER_CHANNEL_REQUIRES_RECIPE:'+','.join(n.type for n in bad))
                if len(mesh.materials)!=1 and not job.get('allow_multi_material_bake'):raise ValueError('MULTI_MATERIAL_BAKE_REQUIRES_EXPLICIT_RECIPE')
            for socket_name in bake_sockets:
                resolution=job.get('bump_bake_resolution',job.get('bake_resolution',2048)) if bump_changes and socket_name=='Normal' else job.get('bake_resolution',2048)
                path=bake_channel(material,bsdf,output,socket_name,obj,out,len(bakes),allow_multi_material=job.get('allow_multi_material_bake',False),resolution=resolution)
                bakes.append(dict(channel=socket_name,texture=str(path.relative_to(ROOT)),sha256=sha(path),resolution=resolution,method='Cycles source-channel bake; tangent space for normals'))
            bad=[]  # Every reachable unsupported channel above has been baked explicitly.
            if bad:
                if len(mesh.materials)!=1:raise ValueError('MULTI_MATERIAL_BAKE_REQUIRES_EXPLICIT_RECIPE')
                for other in objects:other.select_set(False)
                obj.select_set(True);bpy.context.view_layer.objects.active=obj
                original_surface=output.inputs['Surface'].links[0].from_socket
                src=bsdf.inputs['Base Color'].links[0].from_socket
                em=nodes.new('ShaderNodeEmission');links.new(src,em.inputs['Color'])
                for link in list(output.inputs['Surface'].links):links.remove(link)
                links.new(em.outputs[0],output.inputs['Surface'])
                image=bpy.data.images.new('BakedBaseColor',width=2048,height=2048,alpha=False);image.colorspace_settings.name='sRGB'
                tex=nodes.new('ShaderNodeTexImage');tex.image=image
                for n in nodes:n.select=False
                tex.select=True;nodes.active=tex
                scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
                bpy.ops.object.bake(type='EMIT',margin=8,use_clear=True)
                path=out/('base_color_'+str(len(bakes))+'.png');image.filepath_raw=str(path);image.file_format='PNG';image.save();image.pack()
                for link in list(output.inputs['Surface'].links):links.remove(link)
                links.new(original_surface,output.inputs['Surface']);nodes.remove(em)
                for link in list(bsdf.inputs['Base Color'].links):links.remove(link)
                links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
                bakes.append(dict(channel='Base Color',texture=str(path.relative_to(ROOT)),sha256=sha(path),method='Exact upstream source color graph Cycles EMIT bake'))
            # Drop unreachable nodes, not source shader inputs or original appearance.
            reachable=upstream(output.inputs['Surface'])|{output.name}
            for n in list(nodes):
                if n.name not in reachable:nodes.remove(n)
    prepared=out/'prepared.blend'
    # Serialize only this prepared scene's dependencies, not unused source variants/scenes.
    bpy.data.libraries.write(str(prepared),{scene},path_remap='RELATIVE',fake_user=False,compress=True)
    assert sha(source)==before
    write(out/'preparation.json',dict(outcome='PASS',source=job['source'],source_sha256=before,prepared_sha256=sha(prepared),
        selected_meshes=job['meshes'],source_frame=frame,source_unit_scale=source_unit,source_root_rotation_deg=job.get('source_root_rotation_deg',[0,0,0]),bakes=bakes,texture_reductions=texture_reductions,texture_locator_repairs=texture_locator_repairs,surface_pruning=surface_pruning,
        generated_bake_uvs=generated_bake_uvs,producer_sha256=sha(__file__),bake_helper_sha256=sha(ROOT/'scripts/bake_channel.py'),surface_helper_sha256=sha(ROOT/'scripts/source_surface.py'),bump_helper_sha256=sha(ROOT/'scripts/bump_surface.py'),
        scope='Actual source evaluated geometry frozen to one fixed state; no solved soft-body behavior'))
    conversion=dict(blend=str(prepared),source_sha256=sha(prepared),collection=col.name,internal_conversion_authorized=True,
        dimension_bounds_m=job['dimension_bounds_m'],state_id=job['state_id'],output=str(ROOT/job['conversion_dir']),
        scope='REAL_BLENDKIT_BATCH_001_CONTROLLED_LOCAL_TEST',upstream_source_sha256=before)
    write(out/'conversion_job.json',conversion)
    print('REAL_BATCH_SOURCE_PREPARED',job['base_id'],len(objects),'meshes')

if __name__=='__main__':
    job=read(sys.argv[sys.argv.index('--')+1:][0]);prepare(job)
