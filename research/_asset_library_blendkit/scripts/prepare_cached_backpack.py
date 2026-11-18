"""Recover the actual officially downloaded source; select one source LOD and bake its color graph."""
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha

probe=read(ROOT/'reports/cached_backpack_probe.json');source=ROOT/probe['source']
if sha(source)!=probe['sha256']:raise ValueError('OFFICIAL_SOURCE_CHANGED')
out=ROOT/'artifacts/fa971768-8e7e-49dd-93e5-c225b578899e/prepare_a000';out.mkdir(parents=True,exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
obj=bpy.data.objects['BPHighPoly']
if obj.type!='MESH' or len(obj.data.polygons)!=352782:raise ValueError('SOURCE_LOD_IDENTITY_CHANGED')
scene=bpy.data.scenes.new('HotelBackpackPrepared');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
col=bpy.data.collections.new('HotelLibrarySource');scene.collection.children.link(col)
copy=obj.copy();copy.data=obj.data.copy();copy.parent=None;copy.matrix_world=obj.matrix_world.copy();col.objects.link(copy)
copy.hide_render=False;copy.hide_viewport=False;copy.select_set(True);bpy.context.view_layer.objects.active=copy
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.render.bake.margin=8
baked=[]
for index,original in enumerate(list(copy.data.materials)):
    material=original.copy();copy.data.materials[index]=material
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bsdfs=[n for n in nodes if n.type=='BSDF_PRINCIPLED'];outputs=[n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
    if len(bsdfs)!=1 or len(outputs)!=1:raise ValueError('UNSUPPORTED_SOURCE_SHADER')
    bsdf=bsdfs[0];output=outputs[0]
    if any(s.is_linked and s.name!='Base Color' for s in bsdf.inputs):raise ValueError('OTHER_LINKED_CHANNEL_REQUIRES_SEPARATE_BAKE')
    upstream=bsdf.inputs['Base Color'].links[0].from_socket
    emission=nodes.new('ShaderNodeEmission');links.new(upstream,emission.inputs['Color'])
    for link in list(output.inputs['Surface'].links):links.remove(link)
    links.new(emission.outputs[0],output.inputs['Surface'])
    image=bpy.data.images.new('BackpackBakedBaseColor',width=2048,height=2048,alpha=False)
    image.colorspace_settings.name='sRGB'
    target=nodes.new('ShaderNodeTexImage');target.image=image
    for node in nodes:node.select=False
    target.select=True;nodes.active=target
    bpy.ops.object.bake(type='EMIT',use_clear=True,margin=8)
    texture=out/('base_color_'+str(index)+'.png');image.filepath_raw=str(texture);image.file_format='PNG';image.save();image.pack()
    clean=bpy.data.materials.new('Backpack_USD_PBR');clean.use_nodes=True
    clean_bsdf=next(n for n in clean.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for socket in bsdf.inputs:
        if not socket.is_linked and hasattr(socket,'default_value') and socket.name in clean_bsdf.inputs:
            try:clean_bsdf.inputs[socket.name].default_value=socket.default_value
            except (TypeError,ValueError):pass
    tex=clean.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
    clean.node_tree.links.new(tex.outputs['Color'],clean_bsdf.inputs['Base Color'])
    copy.data.materials[index]=clean
    baked.append(dict(material=original.name,texture=str(texture.relative_to(ROOT)),sha256=sha(texture),
        method='Cycles EMIT bake of exact source Base Color graph including RGB Curves and Hue/Saturation',
        remaining_channels='Original unlinked Principled scalar/vector defaults copied'))
prepared=out/'prepared.blend';bpy.ops.wm.save_as_mainfile(filepath=str(prepared))
assert sha(source)==probe['sha256']
report=dict(outcome='PASS',original_source=probe['source'],original_sha256=probe['sha256'],
    prepared=str(prepared.relative_to(ROOT)),prepared_sha256=sha(prepared),collection=col.name,
    selected_source_mesh='BPHighPoly',excluded_source_lod='BPLowPoly',polygons=len(copy.data.polygons),
    reason='Official source contains overlapping high/low geometry; only high LOD selected, one independent asset',bakes=baked)
write(out/'preparation.json',report)
job=dict(blend=str(prepared),source_sha256=sha(prepared),collection=col.name,internal_conversion_authorized=True,
    dimension_bounds_m=dict(min=[.15,.15,.05],max=[.8,.8,.8]),state_id='lying_scan',
    output=str(ROOT/'artifacts/fa971768-8e7e-49dd-93e5-c225b578899e/convert_a000'),
    scope='REAL_OFFICIAL_BLENDKIT_BACKPACK_CONTROLLED_LOCAL_TEST_NO_DISTRIBUTION',
    upstream_source_sha256=probe['sha256'])
write(out/'conversion_job.json',job)
print('REAL_OFFICIAL_BACKPACK_PREPARED',str(prepared),flush=True)
