"""Engineering fixture ONLY. Never a candidate/model substitute or catalog entry."""
import bpy
import hashlib
import json
from pathlib import Path
import sys
root=Path(sys.argv[sys.argv.index('--')+1]).resolve(); root.mkdir(parents=True,exist_ok=False)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_torus_add(major_radius=.12,minor_radius=.025,location=(.4,-.2,.3),major_segments=32,minor_segments=12)
ob=bpy.context.object; ob.name='INFRASTRUCTURE_TORUS_NOT_A_LIBRARY_ASSET'
collection=bpy.data.collections.new('InfrastructureFixture'); bpy.context.scene.collection.children.link(collection)
for c in list(ob.users_collection): c.objects.unlink(ob)
collection.objects.link(ob)
im=bpy.data.images.new('FixtureTexture',width=16,height=16)
pixels=[]
for y in range(16):
    for x in range(16): pixels.extend([.08,.25 if (x//4+y//4)%2 else .65,.8,1.0])
im.pixels=pixels; im.filepath_raw=str(root/'fixture.png'); im.file_format='PNG'; im.save(); im.source='FILE'; im.pack()
mat=bpy.data.materials.new('FixturePBR'); mat.use_nodes=True
tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=im
bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value=.4
ob.data.materials.append(mat)
source=root/'fixture.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(source))
job=dict(blend=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),collection=collection.name,
    internal_conversion_authorized=True,dimension_bounds_m=dict(min=[.1,.1,.01],max=[.5,.5,.2]),
    output=str(root/'conversion'),scope='INFRASTRUCTURE_FIXTURE_NOT_BLENDKIT_NOT_COUNTED')
(root/'job.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
