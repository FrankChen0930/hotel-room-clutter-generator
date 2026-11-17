"""Bounded deterministic geometry sampler; never writes USD or runs physics."""
import math
from .adapters import footprint_supported
from .geometry import intersects,obstacle_hit,rotated_bounds,forbidden_hit
from .identity import rng_for


def place_requests(plan,room,catalog,budget=None,*,attempt_ordinal=0,stream='placement',preferred_supports=None,sample_limits=None):
    from pxr import Gf
    if stream not in ('placement','repair') or type(attempt_ordinal) is not int or attempt_ordinal<0:raise ValueError('PLACEMENT_STREAM')
    budget=budget or plan['budgets'];assets={a['asset_id']:a for a in catalog['entries']}
    moving={room.native_initial[r['source_object_id']]['prim'] for r in plan['requests'] if r['origin']=='native'}
    objects=[];boxes=[];sampling=[]
    for request in plan['requests']:
        asset=assets[request['asset_id']];state=next(s for s in asset['states'] if s['state_id']==request['state_id'])
        rng=rng_for(plan['seed'],stream+'/'+plan['scenario'],request['request_id'],attempt_ordinal)
        supports=list(request['allowed_support_ids']);rng.shuffle(supports)
        spread=plan.get('targets',{}).get('spread',{})
        occupied={o['effective']['support_id'] for o in objects}
        if spread.get('hard') and len(occupied)<spread.get('occupied_support_min',0):supports.sort(key=lambda support:support in occupied)
        preferred=(preferred_supports or {}).get(request['request_id'])
        if preferred in supports:supports.remove(preferred);supports.insert(0,preferred)
        supports=supports[:budget['max_supports']]
        sample_cap=min(budget['max_samples_per_request'],(sample_limits or {}).get(request['request_id'],budget['max_samples_per_request']))
        accepted=None;rejections={};total=0
        for support_id in supports:
            support=room.supports[support_id]
            if support['shape']=='circle':
                center=support['center'];radius=support['radius'];lo=[v-radius for v in center];hi=[v+radius for v in center]
            else:
                lo=[min(p[j] for p in support['polygon']) for j in range(2)]
                hi=[max(p[j] for p in support['polygon']) for j in range(2)]
            obstacles=[o for o in room.obstacles[support_id] if not any(o['prim']==p or o['prim'].startswith(p+'/') for p in moving)]
            for _ in range(budget['samples_per_support']):
                if total>=sample_cap:break
                total+=1;x=rng.uniform(lo[0],hi[0]);y=rng.uniform(lo[1],hi[1]);yaw=rng.uniform(-math.pi,math.pi)
                gap=state['support_envelope']['clearance_m'];z=support['z']+gap-state['visual_bounds'][0][2]
                footprint,box=rotated_bounds(state['visual_bounds'],yaw,x,y,z)
                policy_region=dict(status='SUPPORTED',shape='polygon',polygon=support['allowed_region'])
                reason=('off_support' if not footprint_supported(support,footprint,support['edge_margin_m']) or not footprint_supported(policy_region,footprint,0.) else
                        'forbidden_region' if forbidden_hit(box,room.forbidden_regions) else
                        'obstacle' if any(obstacle_hit(box,o) for o in obstacles) else
                        'object_overlap' if any(intersects(box,b,.002) for b in boxes) else None)
                if reason:rejections[reason]=rejections.get(reason,0)+1;continue
                base=Gf.Matrix4d(*[v for row in state['state_transform'] for v in row])
                matrix=base*Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0,0,1),math.degrees(yaw)))*Gf.Matrix4d().SetTranslate((x,y,z))
                world=[[float(matrix[i][j]) for j in range(4)] for i in range(4)]
                effective=dict(world_matrix=world,state_id=state['state_id'],support_id=support_id,
                               semantic_state=request['semantic_state'],body_mode='kinematic')
                native=room.native_initial.get(request['source_object_id'])
                accepted=dict(instance_id=request['request_id'],request_id=request['request_id'],asset_id=asset['asset_id'],
                    state_sha256=state['sha256'],origin=asset['origin'],source_object_id=request['source_object_id'],
                    native_prim=native['prim'] if native else None,
                    before=dict(exists=True,**native) if native else dict(exists=False),after=dict(effective),effective=dict(effective),
                    expected_bounds=box,footprint=footprint)
                boxes.append(box);break
            if accepted:break
        sampling.append(dict(request_id=request['request_id'],samples=total,rejections=rejections,budget=budget))
        if accepted:objects.append(accepted)
        else:return dict(status='FAIL',objects=objects,sampling=sampling,failure=dict(reason='PLACEMENT_EXHAUSTED',request_id=request['request_id']))
    return dict(status='PASS',objects=objects,sampling=sampling,failure=None)
