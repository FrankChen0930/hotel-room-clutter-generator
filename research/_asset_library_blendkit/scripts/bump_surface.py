"""Narrow translation of shading-only displacement; never changes source geometry."""
def translate_bump_only(material,obj):
    if getattr(material,'displacement_method',None)!='BUMP':return []
    nodes=material.node_tree.nodes;links=material.node_tree.links
    outputs=[n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
    if len(outputs)!=1:return []
    output=outputs[0]
    if not output.inputs['Displacement'].is_linked or not output.inputs['Surface'].is_linked:return []
    disp=output.inputs['Displacement'].links[0].from_node
    bsdf=output.inputs['Surface'].links[0].from_node
    if disp.type!='DISPLACEMENT' or bsdf.type!='BSDF_PRINCIPLED':return []
    if bsdf.inputs['Normal'].is_linked or disp.inputs['Normal'].is_linked:return []
    if any(abs(x)>1e-9 for x in disp.inputs['Normal'].default_value):return []
    scales=list(map(float,obj.matrix_world.to_scale()))
    if obj.matrix_world.determinant()<=0 or min(scales)<=0:return []
    if disp.space=='OBJECT':
        if max(scales)-min(scales)>1e-6*max(scales):return []
        distance=scales[0]
    elif disp.space=='WORLD':distance=1.
    else:return []
    def copy_socket(source,destination):
        if source.is_linked:links.new(source.links[0].from_socket,destination)
        else:destination.default_value=source.default_value
    subtract=nodes.new('ShaderNodeMath');subtract.operation='SUBTRACT'
    copy_socket(disp.inputs['Height'],subtract.inputs[0]);copy_socket(disp.inputs['Midlevel'],subtract.inputs[1])
    multiply=nodes.new('ShaderNodeMath');multiply.operation='MULTIPLY'
    links.new(subtract.outputs[0],multiply.inputs[0]);copy_socket(disp.inputs['Scale'],multiply.inputs[1])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=1;bump.inputs['Distance'].default_value=distance
    links.new(multiply.outputs[0],bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    for link in list(output.inputs['Displacement'].links):links.remove(link)
    return [dict(kind='SHADING_ONLY_DISPLACEMENT_TO_BUMP',source_method='BUMP',space=disp.space,
        object_scale=scales,bump_distance=distance,source_node=disp.name,
        scope='Unlinked source shader normal and geometric displacement normal only; no geometry displacement or deformation. Native review still required.')]
