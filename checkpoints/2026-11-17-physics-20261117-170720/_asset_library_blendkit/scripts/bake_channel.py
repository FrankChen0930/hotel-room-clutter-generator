"""Bake source shader inputs through Blender; never flatten them to constant placeholders."""
import bpy

def bake_channel(material,bsdf,output,socket_name,obj,out,serial,allow_multi_material=False):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
    for item in scene.objects:item.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    normal=socket_name=='Normal'
    image=bpy.data.images.new('Baked_'+socket_name,width=2048,height=2048,alpha=False)
    image.colorspace_settings.name='Non-Color' if normal or socket_name in {'Roughness','Metallic','Alpha'} else 'sRGB'
    tex=nodes.new('ShaderNodeTexImage');tex.image=image
    for n in nodes:n.select=False
    tex.select=True;nodes.active=tex
    temporary=[];scratch=None
    others={m for m in obj.data.materials if m and m!=material}
    if others:
        if not allow_multi_material:raise ValueError('MULTI_MATERIAL_BAKE_REQUIRES_EXPLICIT_RECIPE')
        scratch=bpy.data.images.new('DiscardedOtherMaterialBake',width=4,height=4,alpha=False)
        for other in others:
            if not other.use_nodes:raise ValueError('OTHER_MATERIAL_HAS_NO_NODE_GRAPH')
            other_nodes=other.node_tree.nodes;active=other_nodes.active
            discard=other_nodes.new('ShaderNodeTexImage');discard.image=scratch;other_nodes.active=discard
            temporary.append((other_nodes,discard,active))
    surface=output.inputs['Surface'].links[0].from_socket
    emission=None
    if not normal:
        src=bsdf.inputs[socket_name].links[0].from_socket
        emission=nodes.new('ShaderNodeEmission');links.new(src,emission.inputs['Color'])
        for link in list(output.inputs['Surface'].links):links.remove(link)
        links.new(emission.outputs[0],output.inputs['Surface'])
    try:
        bpy.ops.object.bake(type='NORMAL' if normal else 'EMIT',normal_space='TANGENT',margin=8,use_clear=True)
    finally:
        for other_nodes,discard,active in temporary:other_nodes.remove(discard);other_nodes.active=active
        if scratch and scratch.users==0:bpy.data.images.remove(scratch)
    path=out/(socket_name.lower().replace(' ','_')+'_'+str(serial)+'.png')
    image.filepath_raw=str(path);image.file_format='PNG';image.save();image.pack()
    if emission:
        for link in list(output.inputs['Surface'].links):links.remove(link)
        links.new(surface,output.inputs['Surface']);nodes.remove(emission)
    for link in list(bsdf.inputs[socket_name].links):links.remove(link)
    if normal:
        mapper=nodes.new('ShaderNodeNormalMap');mapper.space='TANGENT'
        links.new(tex.outputs['Color'],mapper.inputs['Color']);links.new(mapper.outputs['Normal'],bsdf.inputs[socket_name])
    else:links.new(tex.outputs['Color'],bsdf.inputs[socket_name])
    return path
