import json,hashlib
from pathlib import Path
from common import *
PREVIOUS=None
VERSION='bedding-visual-1.0'

def overlay(path, seed, assets):
    src = PREVIOUS / ('clean.usda' if seed is None else f'seed_{seed}_preview.usda')
    s = Usd.Stage.CreateNew(str(path))
    root = U.Xform.Define(s, PREFIX)
    s.SetDefaultPrim(root.GetPrim())
    root.GetPrim().GetReferences().AddReference(relative(src, path))
    U.SetStageUpAxis(s, 'Z')
    U.SetStageMetersPerUnit(s, 1)
    manifest = {'seed': seed, 'source_scene': relative(src, path), 'source_scene_sha256': sha(src), 'asset_version': VERSION, 'instances': [], 'status': 'STATIC_PREVIEW', 'geometry': 'VISUAL_ONLY', 'physics': 'NOT_RUN', 'collision': 'NOT_CERTIFIED'}
    if seed is not None:
        old = read(PREVIOUS / f'seed_{seed}_manifest.json')
        manifest.update(scenario=old['scenario'], selector_source=old['soft'])
        for p in list(prims(s)):
            if str(p.GetPath()).startswith(PREFIX + '/V2Soft/BED_') and p.IsA(U.Gprim):
                U.Imageable(p).CreateVisibilityAttr().Set('invisible')
        U.Xform.Define(s, PREFIX + '/RefinedBedding')
        for bed, r in old['soft'].items():
            U.Xform.Define(s, PREFIX + '/RefinedBedding/' + bed)
            cy = r['center_y']
            parent = PREFIX + '/Furniture/' + bed
            s.GetPrimAtPath(parent).SetInstanceable(False)
            names = ('PillowLeft', 'PillowRight') if r['state'] == 'NeatCanonical' else ('Duvet', 'PillowLeft', 'PillowRight')
            for name in names:
                U.Imageable(s.GetPrimAtPath(parent + '/Visual/' + name)).CreateVisibilityAttr().Set('invisible')
            desired = []
            if r['state'] != 'NeatCanonical':
                desired.append(('Duvet', r['state'], pose(0, cy, 0)))
            for i in range(2):
                if r['state'] == 'NeatCanonical':
                    state = 'NeatPillow'
                    m = pose(0.43 - 0.04 * i, cy, 0.579 + 0.192 * i, 3 - 6 * i)
                else:
                    state = 'CompressedPillow' if i == 0 else 'NeatPillow'
                    m = pose(0.4 + 0.04 * i, cy + (-0.34 if i == 0 else 0.34), 0.519, r['pillow_yaws'][i])
                desired.append(('Pillow' + str(i), state, m))
            for name, state, m in desired:
                p = PREFIX + '/RefinedBedding/' + bed + '/' + name
                xf = U.Xform.Define(s, p)
                xf.GetPrim().GetReferences().AddReference(relative(assets[state], path))
                xf.AddTransformOp().Set(m)
                contact = {}
                manifest['instances'].append({'path': p, 'state': state, 'asset_path': assets[state].relative_to(ROOT).as_posix(), 'asset_sha256': sha(assets[state]), 'world_matrix': rows(m), 'parameters': {'fixed_shape_version': VERSION, 'placement_seed': seed, 'stack_contact_edge_drop_m': 0.16 if contact else 0}, 'mesh_override_sha256': contact})
    s.GetRootLayer().customLayerData = {'status': 'STATIC_PREVIEW', 'bedding': 'VISUAL_ONLY', 'physics': 'NOT_RUN', 'collision': 'NOT_CERTIFIED'}
    s.GetRootLayer().Save()
    return manifest
