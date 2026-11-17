"""Inspect only datablocks used by the asset, not every library loaded by Blender."""
def linked_asset_datablocks(objects):
    linked=[];seen=set()
    def check(block):
        if block is None or id(block) in seen:return
        seen.add(id(block))
        if getattr(block,'library',None):linked.append(block.name)
        tree=getattr(block,'node_tree',None)
        if tree:
            check(tree)
            for node in tree.nodes:
                check(getattr(node,'image',None));check(getattr(node,'node_tree',None))
    for obj in objects:
        check(obj);check(getattr(obj,'data',None))
        check(getattr(obj,'instance_collection',None))
        for slot in getattr(obj,'material_slots',[]):check(slot.material)
    return sorted(set(linked))
