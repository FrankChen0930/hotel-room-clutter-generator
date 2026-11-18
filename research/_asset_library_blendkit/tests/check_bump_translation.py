"""Compare actual Cycles source/translated/baked images; fixture never becomes an asset."""
import bpy,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from library import ROOT,write
from bump_surface import translate_bump_only
from bake_channel import bake_channel
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=False
scene.render.resolution_x=96;scene.render.resolution_y=96;scene.render.resolution_percentage=100
scene.world.color=(.03,.03,.03)
bpy.ops.object.light_add(type='SUN',rotation=(math.radians(30),math.radians(35),0));bpy.context.object.data.energy=2
bpy.ops.object.camera_add(location=(0,0,3));camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
folder=ROOT/'reports/bump_translation_check_a000';folder.mkdir(exist_ok=False)
def capture(name):
    scene.cycles.seed=0;scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
    im=bpy.data.images.load(scene.render.filepath,check_existing=False);return list(im.pixels)
def mae(a,b):
    pixels=[(y*96+x)*4+c for y in range(24,72) for x in range(24,72) for c in range(3)]
    return sum(abs(a[i]-b[i]) for i in pixels)/len(pixels)
rows=[]
for scale in (1.,.1):
    bpy.ops.mesh.primitive_plane_add(size=2);obj=bpy.context.object;obj.scale=(scale,scale,scale)
    camera.location=(0,0,3*scale);camera.data.ortho_scale=2.1*scale
    m=bpy.data.materials.new('BumpSource');m.use_nodes=True;m.displacement_method='BUMP';obj.data.materials.append(m)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');out=n.get('Material Output')
    p.inputs['Base Color'].default_value=(.4,.4,.4,1);p.inputs['Specular IOR Level'].default_value=0
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3
    disp=n.new('ShaderNodeDisplacement');disp.inputs['Scale'].default_value=.05
    l.new(noise.outputs['Fac'],disp.inputs['Height'])
    flat=capture('flat_'+str(scale));l.new(disp.outputs[0],out.inputs['Displacement'])
    source=capture('source_'+str(scale));before=[tuple(v.co) for v in obj.data.vertices]
    changes=translate_bump_only(m,obj);assert changes
    translated=capture('translated_'+str(scale))
    bake_channel(m,p,out,'Normal',obj,folder,len(rows),resolution=512)
    baked=capture('baked_'+str(scale))
    row=dict(scale=scale,source_vs_flat=mae(source,flat),source_vs_translated=mae(source,translated),source_vs_baked=mae(source,baked),
             geometry_unchanged=before==[tuple(v.co) for v in obj.data.vertices],recipe=changes)
    rows.append(row);obj.hide_render=True
report=dict(outcome='PASS' if all(x['source_vs_flat']>.002 and x['source_vs_translated']<.02 and x['source_vs_baked']<.03 and x['geometry_unchanged'] for x in rows) else 'FAIL',cases=rows,
    scope='Actual controlled Cycles material regression; no library asset or acceptance count')
write(folder/'result.json',report);print('SOURCE_BUMP_TRANSLATION_MEASURED',report);assert report['outcome']=='PASS'
