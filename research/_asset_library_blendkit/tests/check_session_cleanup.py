"""Actual offline Blender ownership test; no acquired models or library entries created."""
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from library import ROOT,write
from session_cleanup import release_scene

bootstrap=bpy.context.scene;original=bpy.data.objects['Cube'];original_mesh=original.data
unrelated=bpy.data.materials.new('UnrelatedOrphanMustSurvive')
scene=bpy.data.scenes.new('WorkerCleanupTest');scene['hotel_batch_job']=0
owned=bpy.data.objects.new('OwnedWorkerObject',original_mesh.copy());scene.collection.objects.link(owned)
scene.collection.objects.link(original)  # Shared original object must survive.
material=bpy.data.materials.new('OwnedWorkerMaterial');material.use_nodes=True;owned.data.materials.append(material)
group=bpy.data.node_groups.new('OwnedWorkerNestedGroup','ShaderNodeTree')
node=material.node_tree.nodes.new('ShaderNodeGroup');node.node_tree=group
image=bpy.data.images.new('OwnedWorkerImage',width=4,height=4);tex=group.nodes.new('ShaderNodeTexImage');tex.image=image
mesh_name=owned.data.name;image_name=image.name;group_name=group.name;material_name=material.name
bpy.context.window.scene=scene
result=release_scene(scene,bootstrap)
assert bpy.data.objects.get('Cube')==original and original.data==original_mesh
assert original.name in bootstrap.objects and bpy.context.scene==bootstrap
assert bpy.data.materials.get(unrelated.name)==unrelated
assert bpy.data.meshes.get(mesh_name) is None and bpy.data.images.get(image_name) is None
assert bpy.data.node_groups.get(group_name) is None and bpy.data.materials.get(material_name) is None
try:release_scene(bootstrap,bpy.data.scenes.new('OtherBootstrap'))
except ValueError:pass
else:raise AssertionError('Unowned scene accepted')
write(ROOT/'reports/continuous_cleanup_test.json',dict(outcome='PASS',result=result,scope='Actual Blender owned/shared scene resource lifecycle test only; zero asset qualifications'))
print('SCOPED_BLENDER_CLEANUP_PASS')
