"""Offline Blender reference of one actual original material; never edits source files."""
import bpy
from pathlib import Path
import sys
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,read,write,sha

base=sys.argv[sys.argv.index('--')+1];job=read(ROOT/'config'/('job_'+base+'.json'));source=ROOT/job['source']['path'];assert sha(source)==job['source']['sha256']
out=ROOT/'reports'/('source_reference_'+base);out.mkdir(exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
unit=bpy.context.scene.unit_settings.scale_length
scene=bpy.data.scenes.new('SourceMaterialReference');bpy.context.window.scene=scene;objects=[]
for name in job['meshes']:
    original=bpy.data.objects[name];matrix=original.matrix_world.copy();obj=original.copy();obj.parent=None;obj.matrix_world=Matrix.Scale(unit,4)@matrix;scene.collection.objects.link(obj);objects.append(obj)
points=[obj.matrix_world@Vector(corner) for obj in objects for corner in obj.bound_box]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
shift=Matrix.Translation(Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z)))
for obj in objects:obj.matrix_world=shift@obj.matrix_world
native=read(ROOT/'reports/batch003a_native_previews_a000'/('bk-'+base)/'render.json')['cameras']['front']
world=bpy.data.worlds.new('ReferenceWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.92,.95,1,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8;scene.world=world
light=bpy.data.lights.new('ReferenceSun','SUN');light.energy=3;lamp=bpy.data.objects.new('ReferenceSun',light);scene.collection.objects.link(lamp);lamp.rotation_euler=(.436,-.611,.436)
data=bpy.data.cameras.new('ReferenceCamera');camera=bpy.data.objects.new('ReferenceCamera',data);scene.collection.objects.link(camera);camera.location=native['eye'];camera.rotation_euler=(Vector(native['target'])-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=native['focal'];data.sensor_width=36;scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/'front.png')
bpy.ops.render.render(write_still=True)
assert sha(source)==job['source']['sha256']
write(out/'reference.json',dict(outcome='CAPTURED_NOT_QUALIFIED',source=job['source'],image=dict(path=str((out/'front.png').relative_to(ROOT)),sha256=sha(out/'front.png')),scope='Original source shaders in Blender Cycles; source remains unchanged. Renderer/lighting differ from native preview, compare material pattern only.'))
print('ACTUAL_ORIGINAL_MATERIAL_REFERENCE_CAPTURED')
