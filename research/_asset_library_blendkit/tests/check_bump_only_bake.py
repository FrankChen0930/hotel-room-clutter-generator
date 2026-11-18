"""Measure actual Cycles normal baking of BUMP-only displacement; no library asset."""
import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from library import ROOT,write
from bake_channel import bake_channel
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_plane_add(size=2);obj=bpy.context.object
m=bpy.data.materials.new('BumpOnlyRegression');m.use_nodes=True;m.displacement_method='BUMP';obj.data.materials.append(m)
n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');out=n.get('Material Output')
folder=ROOT/'reports/bump_only_bake_check_a000';folder.mkdir(exist_ok=False)
before=[tuple(v.co) for v in obj.data.vertices]
flat=bake_channel(m,p,out,'Normal',obj,folder,0,resolution=256)
flat_image=next(i for i in bpy.data.images if i.filepath_raw==str(flat))
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3
disp=n.new('ShaderNodeDisplacement');disp.inputs['Scale'].default_value=.05
l.new(noise.outputs['Fac'],disp.inputs['Height']);l.new(disp.outputs[0],out.inputs['Displacement'])
bumped=bake_channel(m,p,out,'Normal',obj,folder,1,resolution=256)
bump_image=next(i for i in bpy.data.images if i.filepath_raw==str(bumped))
a=list(flat_image.pixels);b=list(bump_image.pixels)
change=max(abs(a[i]-b[i]) for i in range(len(a)) if i%4 in (0,1))
assert before==[tuple(v.co) for v in obj.data.vertices]
report=dict(outcome='PASS' if change>.01 else 'FAIL_NORMAL_BAKE_IGNORES_DISPLACEMENT',maximum_rg_change=change,
            geometry_unchanged=True,source_method=m.displacement_method,scope='Actual Cycles regression only; engineering fixture never registered or counted as an asset')
write(folder/'result.json',report);print('BUMP_ONLY_NORMAL_BAKE_MEASURED',report)
assert change>.01
