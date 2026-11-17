"""Exact graph pruning only; linked or non-endpoint shader mixes remain unsupported."""
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
