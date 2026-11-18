"""Create the initial Hotel profile/catalog from adopted locators and measured USD.

Never executes historical prepare/generate scripts. Writes only new core config.
"""
from pathlib import Path
import json
import sys
CODE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Gf, Usd, UsdGeom, UsdUtils
from common_core.adapters import extract_support
from common_core.contracts import load_json, validate_contract
from common_core.identity import content_digest, sha256_file
from common_core.room import bounds, geometry_signature, rows


def main():
    workspace=CODE.parent;config=CODE/'config'
    meta_path=workspace/'_hotel705_pilot/roomscale/evidence/adapter.json';meta=load_json(meta_path)
    lock=load_json(config/'source_lock.json');source=lock['rooms']['room_hotel']['root']
    mounts=dict(room_hotel=workspace/'_hotel705_reference/release_v1.0.0/hotel705-random-clutter',
                room_yazhi=workspace/'YAZHI-TWIN',hotel_helpers=workspace/'_hotel705_pilot',
                toolkit=workspace/'_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator')
    room_path=mounts['room_hotel']/source['path']
    if sha256_file(room_path)!=meta['source_sha256']:raise ValueError('HISTORICAL_LOCATOR_SOURCE_MISMATCH')
    s=Usd.Stage.Open(str(room_path));bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy'])
    identity=rows(Gf.Matrix4d(1));closure=lock['rooms']['room_hotel']['closure']
    profile=dict(schema_version='1.0',profile_id='hotel705',profile_version='1.0',
        source={**source,'root_prim':'/root','closure_ref':'source_lock.json#rooms/room_hotel/closure','closure_sha256':content_digest(closure)},
        coordinates=dict(meters_per_unit=1.,up_axis='Z',to_common=identity),supports=[],forbidden_regions=[],
        source_objects=[],override_allowlist=[],test_freeze=dict(body_mode='kinematic',joint_mode='preserve'),cameras=[],
        provenance=dict(kind='MEASURED_SOURCE_USD',locator_metadata_sha256=sha256_file(meta_path),human_confirmed=False))
    for name,item in meta['supports'].items():
        prim=s.GetPrimAtPath(item['collider']);support=extract_support(s,prim)
        if support['status']!='SUPPORTED':raise ValueError('HOTEL_SUPPORT_UNKNOWN: '+name)
        polygon=support['polygon'];lo=[min(p[j] for p in polygon) for j in range(2)]+[support['z']+.0001]
        hi=[max(p[j] for p in polygon) for j in range(2)]+[support['z']+.5]
        profile['supports'].append(dict(support_id=name,prim=item['prim'],collider=item['collider'],kind='mesh_top',
            local_frame=identity,allowed_region=polygon,edge_margin_m=.012,tags=['flat','amenity',name],
            geometry_hash=geometry_signature(prim),obstacle_clip=[lo,hi],
            obstacles=[dict(prim=o['prim'],triangle_refinement='triangle_bounds' in o) for o in item['obstacles']]))
        profile['source_objects'].append(dict(object_id='fixed_'+name,prim=item['prim'],mobility='FIXED',allowed_operations=[]))
    catalog=dict(schema_version='1.0',catalog_id='common-core-adopted',version='1.0',entries=[])
    asset_records={}
    def locate(path):
        path=Path(path).resolve()
        for mount,root in mounts.items():
            if path.is_relative_to(root.resolve()):return dict(mount=mount,path=path.relative_to(root.resolve()).as_posix())
        raise ValueError('ASSET_MOUNT_UNDECLARED: '+str(path))
    def state(state_id,where,signature,visual,base):
        return dict(state_id=state_id,version='1.0',usd_locator_or_native_prim=where,sha256=signature,units=1.,up_axis='Z',
            pivot=[0.,0.,0.],alignment=identity,state_transform=rows(base),visual_bounds=visual,
            footprint=[[visual[0][0],visual[0][1]],[visual[1][0],visual[0][1]],[visual[1][0],visual[1][1]],[visual[0][0],visual[1][1]]],
            support_envelope=dict(clearance_m=.001),allowed_pose_tags=['upright'],acceptance_refs=[],
            physics_proxy=dict(kind='none',capability='STATIC_ONLY',shape_paths=[],geometry_hash=signature))
    for name,item in meta['assets'].items():
        path=Path(item['path']);signature=sha256_file(path)
        if signature!=item['sha256']:raise ValueError('ADOPTED_ASSET_HASH_MISMATCH')
        stage=Usd.Stage.Open(str(path));root=stage.GetDefaultPrim();visual=bounds(root,bbox)
        layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(path))
        if unresolved:raise ValueError('ASSET_DEPENDENCY_UNRESOLVED')
        dependencies=[]
        for dependency in sorted({Path(x.realPath) for x in layers if x.realPath}|{Path(a) for a in assets}):
            record={**locate(dependency),'sha256':sha256_file(dependency),'bytes':dependency.stat().st_size}
            asset_records[(record['mount'],record['path'])]=record;dependencies.append(record)
        where=locate(path);initial=UsdGeom.Xformable(root).ComputeLocalToWorldTransform(0)
        catalog['entries'].append(dict(asset_id=name.lower(),version='1.0',category=name.lower(),origin='external',
            source_locator=where,dependency_hashes=dependencies,root_prim=str(root.GetPath()),
            dimensions=[visual[1][j]-visual[0][j] for j in range(3)],provenance=dict(kind=item['provenance'],human_confirmed=False),
            license_scope='INTERNAL_EVALUATION_ONLY; REDISTRIBUTION_NOT_CLEARED',
            states=[state('default',where,signature,visual,initial)],qualification_refs=[]))
    # Initial native mapping preserves complete visual/collider subtrees. Alignment is data.
    pip_bundles=list(Path('C:/isaac_sim/extscache').glob('omni.kit.pip_archive-*/pip_prebundle'))
    numpy_bundles=[p for p in pip_bundles if (p/'numpy').is_dir()]
    if len(numpy_bundles)!=1:raise ValueError('SDK_NUMPY_BUNDLE_AMBIGUOUS')
    sys.path.insert(0,str(numpy_bundles[0]))
    import numpy as np
    for name,item in meta['amenities'].items():
        p=s.GetPrimAtPath(item['prim']);world=UsdGeom.Xformable(p).ComputeLocalToWorldTransform(0);visual=bounds(p,bbox)
        center=Gf.Vec3d(*[(visual[0][j]+visual[1][j])/2 for j in range(3)])
        points=[]
        for child in Usd.PrimRange(p):
            if child.IsA(UsdGeom.Mesh):
                m=UsdGeom.Mesh(child);xf=UsdGeom.Xformable(child).ComputeLocalToWorldTransform(0)
                points.extend(list(xf.Transform(Gf.Vec3d(q))) for q in m.GetPointsAttr().Get())
        if not points:raise ValueError('NATIVE_POINTS_MISSING: '+name)
        align=Gf.Matrix4d(1);category='water' if name.startswith('Water') else 'mug' if name.startswith('Mug') else 'tea' if name.startswith('Tea') else 'snack'
        if category=='mug':align.SetRotate(Gf.Rotation(Gf.Vec3d(1,0,0),180))
        elif category=='tea':
            cloud=np.array(points);_,axes=np.linalg.eigh(np.cov((cloud-cloud.mean(axis=0)).T))
            normal=Gf.Vec3d(*axes[:,0]);align.SetRotate(Gf.Rotation(normal,Gf.Vec3d(0,0,1)))
        oriented=[list(align.Transform(Gf.Vec3d(q)-center)) for q in points]
        visual=[[min(q[j] for q in oriented) for j in range(3)],[max(q[j] for q in oriented) for j in range(3)]]
        base=world*Gf.Matrix4d().SetTranslate(-center)*align;signature=geometry_signature(p)
        asset_id='native_'+name.lower();ops=['xformOpOrder','xformOp:transform:commoncore','physics:kinematicEnabled','physics:rigidBodyEnabled']
        profile['source_objects'].append(dict(object_id=asset_id,prim=item['prim'],mobility='MOVABLE',allowed_operations=ops,catalog_link=asset_id))
        profile['override_allowlist'].append(dict(prim=item['prim'],attributes=ops))
        catalog['entries'].append(dict(asset_id=asset_id,version='1.0',category=category,origin='native',source_locator=item['prim'],
            room_ids=['hotel705'],source_object_id=asset_id,dependency_hashes=[dict(closure_sha256=content_digest(closure))],root_prim=item['prim'],
            dimensions=[visual[1][j]-visual[0][j] for j in range(3)],provenance=dict(kind='MEASURED_SOURCE_MESH',alignment='ADAPTED_EXISTING_HOTEL_STATE_ALIGNMENT',human_confirmed=False),
            license_scope='INTERNAL_EVALUATION_ONLY; REDISTRIBUTION_NOT_CLEARED',states=[state('default',item['prim'],signature,visual,base)],qualification_refs=[]))
    validate_contract(profile,'RoomProfile');validate_contract(catalog,'Catalog')
    lock['assets']=list(asset_records.values())
    for path,functions in [(meta_path,['adopted locators only']),
        (workspace/'_hotel705_pilot/roomscale/generate.py',['native alignment math reference only'])]:
        record={**locate(path),'sha256':sha256_file(path),'bytes':path.stat().st_size,'functions':functions,'reuse':'read-only reference; no import'}
        if not any(r['mount']==record['mount'] and r['path']==record['path'] for r in lock['helpers']):lock['helpers'].append(record)
    (config/'rooms').mkdir(exist_ok=True)
    for path,data in [(config/'rooms/hotel705.json',profile),(config/'catalog.json',catalog)]:
        with path.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)
    (config/'source_lock.json').write_text(json.dumps(lock,indent=2),encoding='utf-8')
    deploy=dict(bindings={key:str(value) for key,value in mounts.items()},rooms=dict(hotel705='rooms/hotel705.json'),
                catalog='catalog.json',policy='policy.json',source_lock='source_lock.json',isaac_root='C:/isaac_sim')
    with (config/'deployment.local.json').open('x',encoding='utf-8') as stream:json.dump(deploy,stream,indent=2)
    print(json.dumps(dict(supports=len(profile['supports']),native_objects=len(meta['amenities']),catalog_entries=len(catalog['entries']),asset_dependencies=len(asset_records))))


if __name__=='__main__':main()
