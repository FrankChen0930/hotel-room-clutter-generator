"""Independent composed-USD readback; geometric tests do not imply physics."""
import json
from .adapters import footprint_supported,convex_hull
from .geometry import intersects,obstacle_hit,forbidden_hit
from .identity import sha256_file,state_digest,content_digest
from .room import bounds,rows
from .writer import object_prim
from .room import resolve_locator


def composed_footprint(stage,root):
    """Project actual mesh vertices and conservative primitive local extents."""
    from pxr import Gf,Usd,UsdGeom
    points=[]
    for prim in Usd.PrimRange(root,Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Boundable):continue
        xf=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
        if prim.IsA(UsdGeom.Mesh):local=UsdGeom.Mesh(prim).GetPointsAttr().Get()
        else:
            extent=UsdGeom.Boundable(prim).ComputeExtent(Usd.TimeCode.Default())
            if not extent or len(extent)!=2:raise ValueError('UNKNOWN_VISUAL_EXTENT')
            local=[Gf.Vec3d(x,y,z) for x in [extent[0][0],extent[1][0]] for y in [extent[0][1],extent[1][1]] for z in [extent[0][2],extent[1][2]]]
        if local is not None:points.extend(list(xf.Transform(Gf.Vec3d(p)))[:2] for p in local)
    if not points:raise ValueError('UNKNOWN_VISUAL_FOOTPRINT')
    return convex_hull(points)


def validate_static(scene,manifest,room,inputs):
    from pxr import Usd,UsdGeom,UsdUtils,UsdPhysics
    stage=Usd.Stage.Open(str(scene));checks=[];boxes=[];errors=[]
    assets={e['asset_id']:e for e in inputs.catalog['entries']}
    if sha256_file(scene)!=manifest['scene']['sha256']:errors.append('SCENE_HASH_MISMATCH')
    if state_digest(manifest)!=manifest['scene']['state_digest']:errors.append('STATE_DIGEST_MISMATCH')
    if UsdUtils.ComputeAllDependencies(str(scene))[2]:errors.append('UNRESOLVED_DEPENDENCY')
    bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy'])
    moving={o['native_prim'] for o in manifest['objects'] if o['origin']=='native'}
    for obj in manifest['objects']:
        if obj['asset_id'] not in assets:raise ValueError('ASSET_ID_UNKNOWN')
        state=next((s for s in assets[obj['asset_id']]['states'] if s['state_id']==obj['effective']['state_id']),None)
        if state is None:raise ValueError('ASSET_STATE_UNAVAILABLE')
        if state['sha256']!=obj['state_sha256']:errors.append('ASSET_STATE_IDENTITY')
        prim=stage.GetPrimAtPath(object_prim(obj));effective=obj['effective'];support_id=effective['support_id'];support=room.supports[support_id]
        if not prim:errors.append('OBJECT_PRIM_MISSING');continue
        actual=rows(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0));box=bounds(prim,bbox)
        delta=max(abs(actual[i][j]-effective['world_matrix'][i][j]) for i in range(4) for j in range(4))
        footprint=composed_footprint(stage,prim)
        footprint_ok=footprint_supported(support,footprint,0.) and footprint_supported(dict(status='SUPPORTED',shape='polygon',polygon=support['allowed_region']),footprint,0.)
        gap=box[0][2]-support['z'];gap_ok=abs(gap-.001)<=.0001
        obstacles=[o for o in room.obstacles[support_id] if not any(o['prim']==p or o['prim'].startswith(p+'/') for p in moving)]
        collision=any(obstacle_hit(box,o) for o in obstacles) or any(intersects(box,b) for b in boxes) or forbidden_hit(box,room.forbidden_regions)
        semantics=json.loads(prim.GetAttribute('commoncore:semantics').Get())
        semantic_ok=semantics==effective['semantic_state']
        body=UsdPhysics.RigidBodyAPI(prim)
        body_ok=bool(body) and body.GetRigidBodyEnabledAttr().Get() is True and body.GetKinematicEnabledAttr().Get() is True
        if semantics.get('ownership') in ['GUEST','UNKNOWN'] and semantics.get('action_policy')!='DO_NOT_TOUCH':semantic_ok=False
        result=dict(instance_id=obj['instance_id'],matrix_error=delta,actual_bounds=box,gap_m=gap,
                    footprint=footprint_ok,collision=collision,semantics=semantic_ok,body_mode=body_ok)
        checks.append(result);boxes.append(box)
        if delta>1e-8 or not footprint_ok or not gap_ok or collision or not semantic_ok or not body_ok:errors.append('OBJECT_STATIC_FAILED: '+obj['instance_id'])
    allowed={r['prim']:set(r['attributes']) for r in inputs.profile['override_allowlist']}
    def walk(spec):
        path=str(spec.path)
        if path!='/CommonCore' and not path.startswith('/CommonCore/'):
            if set(spec.ListInfoKeys())-{'specifier'}:errors.append('UNAUTHORIZED_SOURCE_METADATA: '+path)
            if spec.properties and (path not in allowed or any(str(p.name) not in allowed[path] for p in spec.properties.values())):
                errors.append('UNAUTHORIZED_SOURCE_OVERRIDE: '+path)
        for child in spec.nameChildren:walk(child)
    for spec in stage.GetRootLayer().rootPrims:walk(spec)
    if len(checks)!=manifest['targets']['count']:errors.append('COUNT_TARGET_MISMATCH')
    categories={assets[o['asset_id']]['category'] for o in manifest['objects']}
    if not set(manifest['targets'].get('required_categories',[]))<=categories:errors.append('REQUIRED_CATEGORY_MISSING')
    for key,count in manifest['targets'].get('required_state_counts',{}).items():
        if sum(o['asset_id']+'/'+o['effective']['state_id']==key for o in manifest['objects'])!=count:errors.append('REQUIRED_STATE_COUNT: '+key)
    scenario=manifest['inputs']['scenario'];level=manifest['inputs']['level'];scenario_cfg=inputs.policy['scenarios'][scenario];level_cfg=inputs.policy['levels'][level]
    eligible=set(scenario_cfg['eligible_categories'])&set(level_cfg.get('eligible_categories',scenario_cfg['eligible_categories']))
    for obj in manifest['objects']:
        category=assets[obj['asset_id']]['category'];allowed=level_cfg.get('allowed_states',{}).get(category)
        if category not in eligible or (allowed is not None and obj['effective']['state_id'] not in allowed):errors.append('POLICY_STATE_ELIGIBILITY')
    from .metrics import composed_metrics,check_targets
    metrics=composed_metrics(scene,manifest,room,inputs.catalog)
    errors.extend(check_targets(metrics,manifest['targets'],inputs.policy,inputs.profile['profile_id'],scenario,level,content_digest(inputs.profile),content_digest(inputs.catalog)))
    return dict(execution='EXECUTED',outcome='FAIL' if errors else 'PASS',target_state_digest=state_digest(manifest),
        scope='composed matrices, conservative visual bounds, planar coverage, source whitelist, semantic metadata and versioned Level metrics; no native query or dynamics',checks=checks,metrics=metrics,errors=errors)


def validate_integrity(inputs,manifest):
    errors=[];records=[*inputs.source_lock['helpers'],*inputs.source_lock.get('assets',[])]
    records.extend(inputs.source_lock['rooms'][inputs.profile['source']['mount']]['closure'])
    for record in records:
        path=resolve_locator(record,inputs.bindings)
        if sha256_file(path)!=record['sha256']:errors.append('DEPENDENCY_HASH_MISMATCH: '+record['path'])
    return dict(execution='EXECUTED',outcome='FAIL' if errors else 'PASS',target_state_digest=state_digest(manifest),
                scope='declared source closure, reused helper and asset bytes after generation',files_checked=len(records),errors=errors)
