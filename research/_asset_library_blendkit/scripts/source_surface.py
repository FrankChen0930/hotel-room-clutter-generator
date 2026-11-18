"""Conservative source graph recipes; glass and arbitrary BSDF mixtures stay blocked."""

def canonicalize_simple_surface(material):
    """Translate only pure emission or a white-transparent/Principled alpha mix."""
    nodes=material.node_tree.nodes;links=material.node_tree.links
    outputs=[n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
    if len(outputs)!=1:return []
    output=outputs[0]
    if not output.inputs['Surface'].is_linked:return []
    surface=output.inputs['Surface'].links[0].from_node
    if surface.type=='EMISSION':
        if surface.inputs['Strength'].is_linked:return []
        bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.inputs['Base Color'].default_value=(0,0,0,1)
        bsdf.inputs['Specular IOR Level'].default_value=0
        bsdf.inputs['IOR'].default_value=1
        bsdf.inputs['Roughness'].default_value=1
        color=surface.inputs['Color']
        if color.is_linked:links.new(color.links[0].from_socket,bsdf.inputs['Emission Color'])
        else:bsdf.inputs['Emission Color'].default_value=color.default_value
        bsdf.inputs['Emission Strength'].default_value=surface.inputs['Strength'].default_value
        links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
        prune_constant_surface(material)
        return [dict(kind='PURE_EMISSION_TO_ZERO_REFLECTANCE_PRINCIPLED',strength=float(bsdf.inputs['Emission Strength'].default_value))]
    if surface.type!='MIX_SHADER':return []
    inputs=surface.inputs
    if not inputs[1].is_linked or not inputs[2].is_linked:return []
    shaders=[inputs[i].links[0].from_node for i in (1,2)]
    if sorted(n.type for n in shaders)!=['BSDF_PRINCIPLED','BSDF_TRANSPARENT']:return []
    transparent=next(n for n in shaders if n.type=='BSDF_TRANSPARENT')
    if transparent.inputs['Color'].is_linked or any(abs(x-1)>1e-6 for x in transparent.inputs['Color'].default_value):return []
    bsdf=next(n for n in shaders if n.type=='BSDF_PRINCIPLED')
    alpha=bsdf.inputs['Alpha'];factor=inputs[0]
    weight=nodes.new('ShaderNodeMath');weight.operation='SUBTRACT' if shaders[0]==bsdf else 'MULTIPLY'
    weight.inputs[0].default_value=1
    if factor.is_linked:links.new(factor.links[0].from_socket,weight.inputs[1])
    else:weight.inputs[1].default_value=factor.default_value
    old_alpha=alpha.links[0].from_socket if alpha.is_linked else None
    multiply=nodes.new('ShaderNodeMath');multiply.operation='MULTIPLY'
    links.new(weight.outputs[0],multiply.inputs[0])
    if old_alpha:links.new(old_alpha,multiply.inputs[1])
    else:multiply.inputs[1].default_value=alpha.default_value
    links.new(multiply.outputs[0],alpha);links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    prune_constant_surface(material)
    return [dict(kind='WHITE_TRANSPARENT_PRINCIPLED_TO_ALPHA',scope='Nonrefracting white transparency only; glass and arbitrary shader mixtures remain blocked')]

def prune_constant_surface(material):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    outputs=[n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output]
    if len(outputs)!=1:return []
    output=outputs[0];changes=[]
    while output.inputs['Surface'].is_linked:
        source=output.inputs['Surface'].links[0].from_node
        if source.type!='MIX_SHADER':break
        factor=source.inputs[0]
        if factor.is_linked or factor.default_value not in (0.,1.):break
        selected=source.inputs[1+int(factor.default_value)]
        if not selected.is_linked:break
        value=selected.links[0].from_socket
        changes.append(dict(kind='EXACT_CONSTANT_SHADER_SELECTION',node=source.name,factor=float(factor.default_value),selected_node=value.node.name))
        for link in list(output.inputs['Surface'].links):links.remove(link)
        links.new(value,output.inputs['Surface'])
    def upstream(socket,seen):
        for link in socket.links:
            n=link.from_node
            if n.name in seen:continue
            seen.add(n.name)
            for inp in n.inputs:upstream(inp,seen)
    reachable={output.name}
    for socket in output.inputs:upstream(socket,reachable)
    for node in list(nodes):
        if node.name not in reachable:nodes.remove(node)
    return changes
