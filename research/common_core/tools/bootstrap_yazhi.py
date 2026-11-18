"""Profile-only second-room adapter using measured existing collider geometry."""
from pathlib import Path
import json
import math
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Gf,Usd,UsdGeom,UsdPhysics
from common_core.adapters import extract_support
from common_core.contracts import load_json,validate_contract
from common_core.identity import content_digest,sha256_file
from common_core.room import rows,bounds,geometry_signature


if __name__=='__main__':
    config=CODE/'config';lock=load_json(config/'source_lock.json');source=lock['rooms']['room_yazhi']['root']
    room=CODE.parent/'YAZHI-TWIN'/source['path'];before=sha256_file(room);stage=Usd.Stage.Open(str(room))
    identity=rows(Gf.Matrix4d(1));bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy'])
    specs=[('round_table','/YAZHI_TWIN/Furniture/ROUND_BLACK_TABLE/CollisionProxies/RoundTop'),
           ('cabinet','/YAZHI_TWIN/Furniture/BEDSIDE_CABINET/CollisionProxies/Top'),
           ('bench','/YAZHI_TWIN/Furniture/WOODEN_BENCH/CollisionProxies/Seat')]
    colliders=[p for p in Usd.PrimRange.Stage(stage,Usd.TraverseInstanceProxies())
               if p.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()]
    profile=dict(schema_version='1.0',profile_id='yazhi',profile_version='1.0',
        source={**source,'root_prim':'/YAZHI_TWIN','closure_ref':'source_lock.json#rooms/room_yazhi/closure',
                'closure_sha256':content_digest(lock['rooms']['room_yazhi']['closure'])},
        coordinates=dict(meters_per_unit=1.,up_axis='Z',to_common=identity),supports=[],forbidden_regions=[],source_objects=[],
        override_allowlist=[],test_freeze=dict(body_mode='kinematic',joint_mode='preserve'),cameras=[],
        provenance=dict(kind='MEASURED_SOURCE_COLLIDERS',human_confirmed=False))
    for name,path in specs:
        prim=stage.GetPrimAtPath(path);surface=extract_support(stage,prim)
        if surface['status']!='SUPPORTED':raise ValueError('SELECTED_YAZHI_SUPPORT_UNKNOWN')
        if surface['shape']=='circle':
            c=surface['center'];r=surface['radius'];polygon=[[c[0]+r*math.cos(2*math.pi*i/64),c[1]+r*math.sin(2*math.pi*i/64)] for i in range(64)]
        else:polygon=surface['polygon']
        lo=[min(p[j] for p in polygon) for j in range(2)]+[surface['z']+.0001]
        hi=[max(p[j] for p in polygon) for j in range(2)]+[surface['z']+.5]
        obstacles=[]
        for collider in colliders:
            if str(collider.GetPath())==path:continue
            a,b=bounds(collider,bbox)
            if all(a[j]<hi[j] and b[j]>lo[j] for j in range(3)):obstacles.append(dict(prim=str(collider.GetPath()),triangle_refinement=False))
        profile['supports'].append(dict(support_id=name,prim=path,collider=path,kind='primitive_top',local_frame=identity,
            allowed_region=polygon,edge_margin_m=.012,tags=['flat','amenity',name],geometry_hash=geometry_signature(prim),obstacles=obstacles))
    for prim in stage.GetPrimAtPath('/YAZHI_TWIN/Furniture').GetChildren():
        profile['source_objects'].append(dict(object_id=prim.GetName(),prim=str(prim.GetPath()),mobility='FIXED',allowed_operations=[]))
    validate_contract(profile,'RoomProfile')
    if sha256_file(room)!=before:raise ValueError('SOURCE_CHANGED')
    with (config/'rooms/yazhi.json').open('x',encoding='utf-8') as stream:json.dump(profile,stream,indent=2)
    deploy=load_json(config/'deployment.local.json');deploy['rooms']['yazhi']='rooms/yazhi.json'
    (config/'deployment.local.json').write_text(json.dumps(deploy,indent=2),encoding='utf-8')
    cameras=dict(overview=dict(eye=[1.8,1.0,2.3],target=[1.8,5.0,.6],focal=14.),round_table=dict(eye=[3.3,6.0,1.8],target=[2.75,7.1,.74],focal=27.))
    with (config/'cameras/yazhi.json').open('x',encoding='utf-8') as stream:json.dump(cameras,stream,indent=2)
    print(json.dumps(dict(supports=[dict(support_id=s['support_id'],obstacles=len(s['obstacles'])) for s in profile['supports']],source_unchanged=True)))
