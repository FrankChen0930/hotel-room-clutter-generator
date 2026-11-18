"""Preserve the second real source's mixed specular tint via a baked texture, not node deletion."""
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha

base='6d5257a4-4fdf-421d-92b9-e77f941f5187';a=next(x for x in read(ROOT/'registry/assets.json')['assets'] if x['source']['asset_base_id']==base)
source=ROOT/a['source']['original_file']['path'];before=sha(source)
out=ROOT/'artifacts'/base/'prepare_a000';out.mkdir(parents=True,exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
obj=bpy.data.objects['Backpack bag'];scene=bpy.data.scenes.new('SecondBackpackPrepared');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
col=bpy.data.collections.new('PreparedSource');scene.collection.children.link(col)
copy=obj.copy();copy.data=obj.data.copy();copy.parent=None;copy.matrix_world=obj.matrix_world.copy();col.objects.link(copy)
copy.hide_render=False;copy.hide_viewport=False;copy.select_set(True);bpy.context.view_layer.objects.active=copy
if len(copy.data.materials)!=1:raise ValueError('SOURCE_MATERIAL_COUNT_CHANGED')
material=copy.data.materials[0].copy();copy.data.materials[0]=material
nodes=material.node_tree.nodes;links=material.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
if bsdf.inputs['Metallic'].is_linked or bsdf.inputs['Metallic'].default_value!=0:raise ValueError('SPECULAR_RECIPE_REQUIRES_DIELECTRIC')
if bsdf.inputs['Specular IOR Level'].is_linked or abs(bsdf.inputs['Specular IOR Level'].default_value-.5)>1e-6:raise ValueError('SOURCE_SPECULAR_IOR_LEVEL_CHANGED')
tint_link=bsdf.inputs['Specular Tint'].links[0];tint_source=tint_link.from_socket
em=nodes.new('ShaderNodeEmission');links.new(tint_source,em.inputs['Color'])
for link in list(output.inputs['Surface'].links):links.remove(link)
links.new(em.outputs[0],output.inputs['Surface'])
image=bpy.data.images.new('BakedSpecularTint',width=2048,height=2048,alpha=False);image.colorspace_settings.name='sRGB'
tex=nodes.new('ShaderNodeTexImage');tex.image=image
for n in nodes:n.select=False
tex.select=True;nodes.active=tex
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
bpy.ops.object.bake(type='EMIT',use_clear=True,margin=8)
texture=out/'specular_tint.png';image.filepath_raw=str(texture);image.file_format='PNG';image.save();image.pack()
for link in list(output.inputs['Surface'].links):links.remove(link)
links.new(bsdf.outputs[0],output.inputs['Surface']);nodes.remove(em)
for link in list(bsdf.inputs['Specular Tint'].links):links.remove(link)
links.new(tex.outputs['Color'],bsdf.inputs['Specular Tint'])
for n in list(nodes):
    if n.type=='MIX' and not any(s.is_linked for s in n.outputs):nodes.remove(n)
prepared=out/'prepared.blend';bpy.ops.wm.save_as_mainfile(filepath=str(prepared))
ior=float(bsdf.inputs['IOR'].default_value);f0=((ior-1)/(ior+1))**2
assert sha(source)==before
write(out/'preparation.json',dict(outcome='PASS',source_sha256=before,prepared_sha256=sha(prepared),source=a['source']['original_file'],
    prepared=str(prepared.relative_to(ROOT)),collection=col.name,baked_channel='Specular Tint',source_ior=ior,f0=f0,
    texture=dict(path=str(texture.relative_to(ROOT)),sha256=sha(texture)),
    preserved_channels=['Base Color image','Roughness image','Normal image/map','Original dielectric IOR'],
    required_usd_mapping='UsdPreviewSurface specular workflow with F0 times baked source tint; standard PBR approximation, requires actual native visual review'))
write(out/'conversion_job.json',dict(blend=str(prepared),source_sha256=sha(prepared),collection=col.name,internal_conversion_authorized=True,
    dimension_bounds_m=dict(min=[.1,.1,.1],max=[.8,.8,.9]),state_id='upright_scan',
    output=str(ROOT/'artifacts'/base/'convert_a000'),scope='REAL_OFFICIAL_BLENDKIT_SECOND_BACKPACK_CONTROLLED_LOCAL_TEST'))
print('SECOND_BACKPACK_SPECULAR_TINT_BAKED',f0)
