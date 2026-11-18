"""Read a downloaded official cache blend without executing file scripts; report structure only."""
import bpy
from mathutils import Vector
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from library import ROOT,write,sha
args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[0]).resolve(strict=True)
if not source.is_relative_to(ROOT/'sources'):raise ValueError('SOURCE_OUTSIDE_PRIVATE_LIBRARY')
before=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
def world_bounds(obj):
    if obj.type!='MESH':return None
    unit=bpy.context.scene.unit_settings.scale_length
    corners=[(obj.matrix_world@Vector(c))*unit for c in obj.bound_box]
    lo=[min(c[i] for c in corners) for i in range(3)]
    hi=[max(c[i] for c in corners) for i in range(3)]
    return dict(min=lo,max=hi,dimensions=[hi[i]-lo[i] for i in range(3)],scope='Source world axes including parent transforms, meters; not local obj.dimensions')
report=dict(source=str(source.relative_to(ROOT)),sha256=before,units=bpy.context.scene.unit_settings.scale_length,
    scenes=[dict(name=s.name,objects=len(s.objects)) for s in bpy.data.scenes],
    collections=[dict(name=c.name,objects=len(c.all_objects),library=bool(c.library)) for c in bpy.data.collections],
    libraries=[dict(name=x.name,filepath=x.filepath,users=x.users) for x in bpy.data.libraries],
    objects=[dict(name=o.name,type=o.type,library=bool(o.library),instance_type=o.instance_type,
        dimensions=list(o.dimensions),world_bounds_m=world_bounds(o),hide_render=o.hide_render,hide_viewport=o.hide_viewport,hidden=o.hide_get(),
        polygons=len(o.data.polygons) if o.type=='MESH' else None,
        metadata_keys=list((o.get('asset_data') or {}).keys())) for o in bpy.data.objects],
    images=[dict(name=i.name,source=i.source,packed=bool(i.packed_file),library=bool(i.library),size=list(i.size)) for i in bpy.data.images],
    materials=[dict(name=m.name,library=bool(m.library),nodes=[dict(name=n.name,type=n.type,linked=any(s.is_linked for s in n.outputs)) for n in m.node_tree.nodes] if m.node_tree else [],
        links=[dict(source=l.from_node.type,source_socket=l.from_socket.name,target=l.to_node.type,target_socket=l.to_socket.name) for l in m.node_tree.links] if m.node_tree else [],
        principled_defaults={s.name:s.default_value if isinstance(s.default_value,(float,int)) else list(s.default_value) for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED' for s in n.inputs if hasattr(s,'default_value') and not s.is_linked} if m.node_tree else {}) for m in bpy.data.materials])
assert sha(source)==before
output=Path(args[1]).resolve() if len(args)>1 else ROOT/'reports/cached_backpack_probe.json'
if not output.is_relative_to(ROOT/'reports'):raise ValueError('WORKLINE_REPORT_REQUIRED')
if output.exists() and len(args)>1:raise ValueError('NEW_PROBE_REPORT_REQUIRED')
write(output,report)
print('OFFICIAL_CACHE_BLEND_PROBE',len(report['objects']),'objects',len(report['libraries']),'libraries',len(report['images']),'images')
