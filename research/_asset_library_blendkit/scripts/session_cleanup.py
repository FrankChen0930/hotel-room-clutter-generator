"""Release only a completed collector scene and its orphaned owned dependencies."""
def release_scene(scene,bootstrap):
    import bpy
    if scene is None or scene==bootstrap:return {}
    if 'hotel_batch_job' not in scene:raise ValueError('NOT_A_WORKER_SCENE')
    objects=list(scene.objects);data=set();materials=set();images=set();groups=set();collections=list(scene.collection.children)
    def visit(tree):
        if not tree:return
        for node in tree.nodes:
            if node.type=='TEX_IMAGE' and node.image:images.add(node.image)
            if node.type=='GROUP' and node.node_tree and node.node_tree not in groups:
                groups.add(node.node_tree);visit(node.node_tree)
    for obj in objects:
        if obj.data:data.add(obj.data)
        for slot in obj.material_slots:
            if slot.material:materials.add(slot.material);visit(slot.material.node_tree)
    bpy.context.window.scene=bootstrap
    removed=0
    for obj in objects:
        if all(s==scene for s in obj.users_scene):bpy.data.objects.remove(obj,do_unlink=True);removed+=1
    bpy.data.scenes.remove(scene)
    for col in collections:
        if col.users==0:bpy.data.collections.remove(col)
    for item in data:
        if item.users==0:
            pool=bpy.data.meshes if isinstance(item,bpy.types.Mesh) else bpy.data.curves if isinstance(item,bpy.types.Curve) else None
            if pool is not None:pool.remove(item)
    for material in materials:
        if material.users==0:bpy.data.materials.remove(material)
    pending=list(groups)
    while pending:
        deletable=[group for group in pending if group.users==0]
        if not deletable:break
        for group in deletable:pending.remove(group);bpy.data.node_groups.remove(group)
    for image in images:
        if image.users==0:bpy.data.images.remove(image)
    return dict(objects_removed=removed,scope='Completed worker scene owned dependencies only; original source files and unrelated startup data untouched')
