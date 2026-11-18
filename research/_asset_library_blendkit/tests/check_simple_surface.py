"""Actual Blender material graph regression checks, never library asset evidence."""
import bpy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from source_surface import canonicalize_simple_surface
from library import ROOT,write

def value(socket):
    if not socket.is_linked:return float(socket.default_value)
    n=socket.links[0].from_node
    if n.type=='VALUE':return n.outputs[0].default_value
    a,b=(value(n.inputs[i]) for i in (0,1))
    return a-b if n.operation=='SUBTRACT' else a*b

checks=0
for reversed_order in (False,True):
    for linked in (False,True):
        m=bpy.data.materials.new('AlphaTranslationRegression');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
        bsdf=n.get('Principled BSDF');bsdf.inputs['Alpha'].default_value=.8
        transparent=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=.3
        if linked:
            factor=n.new('ShaderNodeValue');factor.outputs[0].default_value=.3;l.new(factor.outputs[0],mix.inputs[0])
        l.new(bsdf.outputs[0],mix.inputs[2 if reversed_order else 1]);l.new(transparent.outputs[0],mix.inputs[1 if reversed_order else 2])
        out=n.get('Material Output');l.new(mix.outputs[0],out.inputs['Surface'])
        assert canonicalize_simple_surface(m)
        expected=.8*(.3 if reversed_order else .7)
        assert abs(value(bsdf.inputs['Alpha'])-expected)<1e-6
        assert out.inputs['Surface'].links[0].from_node==bsdf;checks+=1
m=bpy.data.materials.new('TintedTransparencyMustRemainUnsupported');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
t=n.new('ShaderNodeBsdfTransparent');t.inputs['Color'].default_value=(1,.4,1,1);mix=n.new('ShaderNodeMixShader')
l.new(n.get('Principled BSDF').outputs[0],mix.inputs[1]);l.new(t.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],n.get('Material Output').inputs['Surface'])
assert canonicalize_simple_surface(m)==[];checks+=1
m=bpy.data.materials.new('PureEmissionRegression');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
em=n.new('ShaderNodeEmission');em.inputs['Color'].default_value=(.2,.4,.6,1);em.inputs['Strength'].default_value=3
out=n.get('Material Output');l.new(em.outputs[0],out.inputs['Surface']);assert canonicalize_simple_surface(m)
p=out.inputs['Surface'].links[0].from_node
assert p.type=='BSDF_PRINCIPLED' and p.inputs['IOR'].default_value==1 and p.inputs['Specular IOR Level'].default_value==0
assert p.inputs['Emission Strength'].default_value==3;checks+=1
write(ROOT/'reports/simple_surface_graph_check.json',dict(outcome='PASS',cases=checks,
      scope='Actual Blender source graph translation checks only; no real asset or visual acceptance inferred'))
print('SIMPLE_SURFACE_SOURCE_GRAPH_CHECK_PASS',checks)
