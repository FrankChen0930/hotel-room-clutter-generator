"""Author only a new overlay, using effective poses and explicit parent inverse."""
import json
import os
from pathlib import Path
from .room import resolve_locator


def relative_arc(path,parent):return os.path.relpath(path,parent).replace('\\','/')


def object_prim(obj):
    if obj['origin']=='native':return obj['native_prim']
    from .identity import content_digest
    return '/CommonCore/i_'+content_digest(obj['instance_id'])[:24]


def set_world(prim,matrix):
    from pxr import Gf,UsdGeom
    xf=UsdGeom.Xformable(prim);parent=UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(0)
    desired=Gf.Matrix4d(*[v for row in matrix for v in row]);xf.ClearXformOpOrder()
    xf.AddTransformOp(opSuffix='commoncore').Set(desired*parent.GetInverse())


def write_scene(output: Path,inputs,placements):
    from pxr import Sdf,Usd,UsdGeom,UsdPhysics
    output=Path(output)
    from .paths import guard_new_output
    guard_new_output(output)
    from .contracts import verify_source
    assets={a['asset_id']:a for a in inputs.catalog['entries']};references={}
    source=resolve_locator(inputs.profile['source'],inputs.bindings)
    verify_source(source,inputs.profile['source']['sha256'])
    allow={o['prim']:set(o['attributes']) for o in inputs.profile['override_allowlist']}
    for obj in placements['objects']:
        if obj['origin']=='native':
            required={'xformOpOrder','xformOp:transform:commoncore','physics:kinematicEnabled','physics:rigidBodyEnabled','commoncore:semantics'}
            if 'mass_kg' in obj['effective']:required.add('physics:mass')
            if obj['native_prim'] not in allow or not required<=allow[obj['native_prim']]:raise ValueError('SOURCE_OVERRIDE_NOT_ALLOWED')
        else:
            asset=assets[obj['asset_id']]
            state=next((s for s in asset.get('states',[]) if s['state_id']==obj['effective']['state_id']),None)
            if asset.get('states') and state is None:raise ValueError('ASSET_STATE_UNAVAILABLE')
            location=state['usd_locator_or_native_prim'] if state else asset['source_locator']
            root=state.get('root_prim',asset['root_prim']) if state else asset['root_prim']
            path=resolve_locator(location,inputs.bindings)
            if state:
                verify_source(path,state['sha256'])
                if obj.get('state_sha256')!=state['sha256']:raise ValueError('ASSET_STATE_IDENTITY')
            references[obj['instance_id']]=(path,root)
    stage=Usd.Stage.CreateNew(str(output))
    stage.GetRootLayer().subLayerPaths=[relative_arc(source,output.parent)]
    stage.SetDefaultPrim(stage.GetPrimAtPath(inputs.profile['source']['root_prim']))
    UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.Xform.Define(stage,'/CommonCore')
    for obj in placements['objects']:
        asset=assets[obj['asset_id']];path=object_prim(obj)
        if obj['origin']=='native':prim=stage.GetPrimAtPath(path)
        else:
            prim=UsdGeom.Xform.Define(stage,path).GetPrim()
            reference,root=references[obj['instance_id']]
            prim.GetReferences().AddReference(relative_arc(reference,output.parent),root)
        if not prim:raise ValueError('OBJECT_PRIM_MISSING')
        set_world(prim,obj['effective']['world_matrix'])
        body=UsdPhysics.RigidBodyAPI(prim) if prim.HasAPI(UsdPhysics.RigidBodyAPI) else UsdPhysics.RigidBodyAPI.Apply(prim)
        body.CreateRigidBodyEnabledAttr(True);body.CreateKinematicEnabledAttr(True)
        if 'mass_kg' in obj['effective']:UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(obj['effective']['mass_kg'])
        prim.CreateAttribute('commoncore:semantics',Sdf.ValueTypeNames.String).Set(json.dumps(obj['effective']['semantic_state'],sort_keys=True,separators=(',',':')))
    stage.GetRootLayer().Save()
    return stage
