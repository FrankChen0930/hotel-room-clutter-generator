"""Versioned conservative footprint metrics on fixed annotated support masks."""
from collections import Counter
import math
from .adapters import area,convex_hull,intersection

VERSION='canonical-state-polygons-v1'


def summarize(records,room):
    denominator=sum(area(s['allowed_region']) for s in room.supports.values())
    if denominator<=0:raise ValueError('METRICS_EMPTY_SUPPORT_MASK')
    for i,record in enumerate(records):
        for previous in records[:i]:
            if record['support_id']==previous['support_id'] and area(intersection(record['footprint'],previous['footprint']))>1e-8:
                raise ValueError('METRICS_PROJECTED_FOOTPRINT_OVERLAP')
    by_support={key:sum(area(r['footprint']) for r in records if r['support_id']==key) for key in room.supports}
    allpoints=[p for s in room.supports.values() for p in s['allowed_region']]
    diagonal=math.hypot(*(max(p[j] for p in allpoints)-min(p[j] for p in allpoints) for j in range(2)))
    centers=[[sum(p[j] for p in r['footprint'])/len(r['footprint']) for j in range(2)] for r in records]
    mean=[sum(p[j] for p in centers)/len(centers) for j in range(2)] if centers else [0.,0.]
    spread=math.sqrt(sum(sum((p[j]-mean[j])**2 for j in range(2)) for p in centers)/len(centers))/diagonal if centers and diagonal else 0.
    return dict(version=VERSION,count=len(records),coverage=sum(by_support.values())/denominator,denominator_m2=denominator,
        area_by_support_m2=by_support,occupied_supports=len({r['support_id'] for r in records}),normalized_centroid_spread=spread,
        category_counts=dict(Counter(r['category'] for r in records)),state_counts=dict(Counter(r['asset_id']+'/'+r['state_id'] for r in records)),
        method='disjoint conservative canonical-state polygons / fixed annotated support-mask area; obstacles are separate 3D gates and do not change denominator')


def placement_metrics(objects,room,catalog):
    assets={a['asset_id']:a for a in catalog['entries']}
    return summarize([dict(footprint=o['footprint'],support_id=o['effective']['support_id'],category=assets[o['asset_id']]['category'],
        asset_id=o['asset_id'],state_id=o['effective']['state_id']) for o in objects],room)


def composed_metrics(scene,manifest,room,catalog):
    from pxr import Gf,Usd,UsdGeom
    from .writer import object_prim
    stage=Usd.Stage.Open(str(scene));assets={a['asset_id']:a for a in catalog['entries']};records=[]
    for obj in manifest['objects']:
        asset=assets[obj['asset_id']];state=next(s for s in asset['states'] if s['state_id']==obj['effective']['state_id'])
        base=Gf.Matrix4d(*[v for row in state['state_transform'] for v in row])
        actual=UsdGeom.Xformable(stage.GetPrimAtPath(object_prim(obj))).ComputeLocalToWorldTransform(0)
        delta=base.GetInverse()*actual
        if any(abs(delta[i][2])>1e-8 or abs(delta[2][i])>1e-8 for i in range(2)) or abs(delta[2][2]-1)>1e-8:
            raise ValueError('METRICS_UNSUPPORTED_POSE_DELTA')
        lo,hi=state['visual_bounds']
        points=[list(delta.Transform(Gf.Vec3d(x,y,z)))[:2] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]]
        records.append(dict(footprint=convex_hull(points),support_id=obj['effective']['support_id'],category=asset['category'],
                            asset_id=asset['asset_id'],state_id=state['state_id']))
    return summarize(records,room)


def check_targets(metrics,targets,policy,room_id,scenario,level,profile_hash,catalog_hash):
    errors=[]
    if metrics['count']!=targets['count']:errors.append('METRICS_COUNT_TARGET')
    if policy.get('release_frozen'):
        frozen=policy['metrics'];room=frozen['rooms'][room_id]
        if frozen['version']!=VERSION:errors.append('METRICS_VERSION')
        if room['profile_hash']!=profile_hash or frozen['catalog_hash']!=catalog_hash:errors.append('FROZEN_INPUT_IDENTITY')
        if abs(room['denominator_m2']-metrics['denominator_m2'])>1e-9:errors.append('FROZEN_DENOMINATOR')
        lo,hi=room['coverage'][scenario][level]
        if not lo-1e-9<=metrics['coverage']<=hi+1e-9:errors.append('COVERAGE_HARD_TARGET')
        spread=targets['spread']
        if spread.get('hard') and metrics['occupied_supports']<spread['occupied_support_min']:errors.append('SPREAD_HARD_TARGET')
    return errors
