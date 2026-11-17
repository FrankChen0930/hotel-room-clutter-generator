"""Resolve logical inputs and build measured caches from read-only source stages."""
from dataclasses import dataclass
from pathlib import Path

from .contracts import load_json, validate_contract, verify_source
from .contract_validation import locator
from .identity import content_digest, sha256_file


@dataclass(frozen=True)
class Inputs:
    profile: dict
    catalog: dict
    policy: dict | None
    bindings: dict
    source_lock: dict


@dataclass(frozen=True)
class RoomCache:
    cache_key: str
    source_path: Path
    source_identity: str
    supports: dict
    obstacles: dict
    native_initial: dict
    forbidden_regions: tuple = ()


def resolve_locator(value: dict, bindings: dict) -> Path:
    locator(value)
    if value['mount'] not in bindings:raise ValueError('MISSING_MOUNT: '+value['mount'])
    root=Path(bindings[value['mount']]).resolve(strict=True)
    path=(root/value['path']).resolve(strict=True)
    if not path.is_relative_to(root):raise ValueError('SOURCE_PATH_ESCAPE')
    return path


def load_inputs(config_path: Path, room_id: str, require_policy=True) -> Inputs:
    config_path=Path(config_path).resolve(strict=True);config=load_json(config_path);anchor=config_path.parent
    def path(value):return (anchor/value).resolve(strict=True)
    bindings={key:str(path(value)) for key,value in config['bindings'].items()}
    if room_id not in config['rooms']:raise ValueError('UNKNOWN_ROOM: '+room_id)
    profile=validate_contract(load_json(path(config['rooms'][room_id])),'RoomProfile')
    catalog=validate_contract(load_json(path(config['catalog'])),'Catalog')
    policy=validate_contract(load_json(path(config['policy'])),'Policy') if require_policy else None
    if policy and policy.get('release_frozen'):
        if profile['profile_id'] not in policy['metrics']['rooms']:raise ValueError('FROZEN_ROOM_UNSUPPORTED')
        if policy['metrics']['rooms'][profile['profile_id']]['profile_hash']!=content_digest(profile) or policy['metrics']['catalog_hash']!=content_digest(catalog):
            raise ValueError('FROZEN_INPUT_IDENTITY')
    lock=load_json(path(config['source_lock']))
    for record in [*lock.get('helpers',[]),*lock.get('assets',[])]:
        verify_source(resolve_locator(record,bindings),record['sha256'])
    for entry in catalog['entries']:
        if entry['origin']=='external':
            for state in entry['states']:
                verify_source(resolve_locator(state['usd_locator_or_native_prim'],bindings),state['sha256'])
    room=lock['rooms'][profile['source']['mount']]
    if room['unresolved'] or not room['closure_verified']:raise ValueError('UNRESOLVED_SOURCE_CLOSURE')
    for record in room['closure']:verify_source(resolve_locator(record,bindings),record['sha256'])
    if profile['source']['closure_sha256']!=content_digest(room['closure']):raise ValueError('SOURCE_CLOSURE_IDENTITY')
    verify_source(resolve_locator(profile['source'],bindings),profile['source']['sha256'])
    return Inputs(profile,catalog,policy,bindings,lock)


def rows(matrix):return [[float(matrix[i][j]) for j in range(4)] for i in range(4)]


def bounds(prim, cache):
    result=cache.ComputeWorldBound(prim).ComputeAlignedRange()
    return [list(result.GetMin()),list(result.GetMax())]


def geometry_signature(root):
    from pxr import Usd, UsdGeom, UsdPhysics
    records=[]
    for prim in Usd.PrimRange(root,Usd.TraverseInstanceProxies()):
        if prim.IsA(UsdGeom.Gprim) or prim.HasAPI(UsdPhysics.CollisionAPI):
            attrs={a.GetName():str(a.Get()) for a in prim.GetAttributes() if a.GetName() in
                   ('points','faceVertexIndices','faceVertexCounts','size','radius','height','axis','physics:collisionEnabled')}
            records.append(dict(path=str(prim.GetPath()),type=prim.GetTypeName(),attributes=attrs,
                                world=rows(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0))))
    return content_digest(records)


def prepare_room(profile: dict, bindings: dict) -> RoomCache:
    from pxr import Usd, UsdGeom
    from .adapters import extract_support
    validate_contract(profile,'RoomProfile')
    source=resolve_locator(profile['source'],bindings);verify_source(source,profile['source']['sha256'])
    stage=Usd.Stage.Open(str(source))
    if not stage:raise ValueError('SOURCE_OPEN_FAILED')
    coord=profile['coordinates'];identity=[[float(i==j) for j in range(4)] for i in range(4)]
    if (UsdGeom.GetStageMetersPerUnit(stage)!=coord['meters_per_unit'] or UsdGeom.GetStageUpAxis(stage)!=coord['up_axis']
        or coord['meters_per_unit']!=1 or coord['up_axis']!='Z' or coord['to_common']!=identity):
        raise ValueError('UNSUPPORTED_COORDINATE_CONVERSION')
    support_cache={};obstacles={};native={};bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy'])
    for spec in profile['supports']:
        p=stage.GetPrimAtPath(spec['collider'])
        if not p:raise ValueError('SUPPORT_COLLIDER_MISSING')
        signature=geometry_signature(p)
        if spec.get('geometry_hash')!=signature:raise ValueError('SUPPORT_COLLIDER_IDENTITY')
        support=extract_support(stage,p)
        if support['status']!='SUPPORTED':raise ValueError('SUPPORT_GEOMETRY_UNKNOWN: '+support.get('reason',''))
        support_cache[spec['support_id']]={**support,**{k:spec[k] for k in ['edge_margin_m','tags','allowed_region']}}
        items=[]
        for obstacle in spec.get('obstacles',[]):
            prim=stage.GetPrimAtPath(obstacle['prim'])
            if not prim:raise ValueError('OBSTACLE_PRIM_MISSING')
            # Large legacy wall groups use a conservative per-triangle broad phase.
            if obstacle.get('triangle_refinement') and prim.IsA(UsdGeom.Mesh):
                mesh=UsdGeom.Mesh(prim);xf=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
                points=[list(xf.Transform(p)) for p in mesh.GetPointsAttr().Get()];offset=0;pieces=[]
                ids=mesh.GetFaceVertexIndicesAttr().Get()
                region=spec['obstacle_clip'];lo,hi=region
                for count in mesh.GetFaceVertexCountsAttr().Get():
                    face=ids[offset:offset+count];offset+=count
                    for i in range(1,count-1):
                        tri=[points[face[k]] for k in (0,i,i+1)]
                        a=[min(v[j] for v in tri) for j in range(3)];b=[max(v[j] for v in tri) for j in range(3)]
                        if all(a[j]<hi[j] and b[j]>lo[j] for j in range(3)):pieces.append([a,b])
                items.append(dict(prim=obstacle['prim'],triangle_bounds=pieces))
            else:items.append(dict(prim=obstacle['prim'],bounds=bounds(prim,bbox)))
        obstacles[spec['support_id']]=items
    for obj in profile['source_objects']:
        if obj['mobility']!='MOVABLE':continue
        p=stage.GetPrimAtPath(obj['prim'])
        if not p:raise ValueError('NATIVE_PRIM_MISSING')
        native[obj['object_id']]=dict(prim=obj['prim'],world_matrix=rows(UsdGeom.Xformable(p).ComputeLocalToWorldTransform(0)),
            visual_bounds=bounds(p,bbox),geometry_hash=geometry_signature(p))
    verify_source(source,profile['source']['sha256'])
    key=content_digest(dict(profile=profile,source=profile['source']['closure_sha256'],
                            extractor=sha256_file(Path(__file__).with_name('adapters.py')),
                            cache_builder=sha256_file(Path(__file__))))
    return RoomCache(key,source,profile['source']['closure_sha256'],support_cache,obstacles,native,tuple(profile['forbidden_regions']))
