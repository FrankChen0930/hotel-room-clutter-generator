"""Actual Blender graph identity checks; creates no asset or model qualification."""
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from source_surface import prune_constant_surface
from library import ROOT,write

def case(value,linked=False):
    m=bpy.data.materials.new('ConstantMixTest');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    a=n.get('Principled BSDF');b=n.new('ShaderNodeBsdfPrincipled');out=n.get('Material Output');mix=n.new('ShaderNodeMixShader')
    l.new(a.outputs[0],mix.inputs[1]);l.new(b.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface']);mix.inputs[0].default_value=value
    if linked:l.new(n.new('ShaderNodeFresnel').outputs[0],mix.inputs[0])
    chosen=b if value==1 else a;changes=prune_constant_surface(m)
    if not linked and value in (0,1):assert len(changes)==1 and out.inputs['Surface'].links[0].from_node==chosen
    else:assert not changes and out.inputs['Surface'].links[0].from_node==mix

case(0);case(1);case(.5);case(1,True)
m=bpy.data.materials.new('DisplacementMustSurvive');m.use_nodes=True;n=m.node_tree.nodes;d=n.new('ShaderNodeDisplacement')
m.node_tree.links.new(d.outputs[0],n.get('Material Output').inputs['Displacement']);prune_constant_surface(m);assert n.get(d.name)==d
write(ROOT/'reports/constant_surface_graph_check.json',dict(outcome='PASS',cases=5,scope='Exact unlinked endpoint mixes only; fractional/linked mixes and connected displacement preserved, never approximated'))
print('EXACT_CONSTANT_SURFACE_GRAPH_CHECK_PASS')
