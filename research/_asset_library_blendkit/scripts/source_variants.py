"""Conservative pre-screen of likely colorways; exact geometry is checked after conversion."""
from batch_selection import normalized
COLORS=set('black white red blue green pink purple yellow orange grey gray silver gold aluminium aluminum starlight obsidian pearl sky light dark space navy ivory lavender'.split())

def candidate_variant_key(asset,probe):
    author=str(asset.get('author','')).strip().casefold()
    if not author or 'unknown' in author:return None
    family=' '.join(word for word in normalized(asset['name']).split() if word not in COLORS)
    meshes=[o for o in probe['objects'] if o['type']=='MESH' and not o['hidden'] and not o['hide_render']]
    if not family or not meshes or any(not o.get('polygons') or not o.get('world_bounds_m') for o in meshes):return None
    shape=tuple(sorted((o['polygons'],tuple(round(x,6) for x in sorted(o['world_bounds_m']['dimensions']))) for o in meshes))
    return author,asset['category'],family,shape
