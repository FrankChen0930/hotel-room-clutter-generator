import sys,os,json,math,random,itertools
from pathlib import Path
from datetime import datetime,timezone
from common import *
import generate as g
CONFIG=read(CONFIG_DIR/'config.json')

def relation(records):
    result={}
    for chair,table in [('WINDOW_CHAIR_LEFT','SMALL_COFFEE_TABLE'),('WINDOW_CHAIR_RIGHT','ROUND_BLACK_TABLE')]:
        c=records[chair]['destination_pivot_m'];t=records[table]['destination_pivot_m']
        desired=math.degrees(math.atan2(t[0]-c[0],-(t[1]-c[1])))
        error=abs((records[chair]['yaw_delta_degrees']-desired+180)%360-180)
        distance=math.dist(c[:2],t[:2])
        result[chair]={'supporting_table':table,'center_distance_m':distance,'facing_error_degrees':error,
                      'pass':CONFIG['chair_support_distance_m'][0]<=distance<=CONFIG['chair_support_distance_m'][1] and error<=CONFIG['chair_facing_tolerance_degrees']}
    return result

def furniture_checks(source,groups,colliders,records):
    # Only changed furniture is recertified; baseline bench/wall contact is not new drift.
    movable=[k for k in groups if k!='WOODEN_BENCH']
    excluded={p for k in movable for p in groups[k]['colliders']}|{g.FLOOR}
    envelopes={k:g.box_shape(groups[k]['visual_envelope'],mat(records[k]['delta'])) for k in movable}
    for k,e in envelopes.items():
        if not g.contains(colliders[g.FLOOR],e,.02) or abs(e['z_min']-colliders[g.FLOOR]['z_max'])>.001:return False
        if any(g.pair(e,b,.01)!='PASS' for p,b in colliders.items() if p not in excluded):return False
        if any(g.pair(e,g.box_shape(CONFIG[zone]),.01)!='PASS' for zone in ('reserved_strip','entry_keepout')):return False
    if any(g.pair(a,b,.01)!='PASS' for a,b in itertools.combinations(envelopes.values(),2)):return False
    return all(v['pass'] for v in relation(records).values()) and all(r['xy_displacement_m']<=CONFIG['max_furniture_displacement_m'] for r in records.values())

def furniture(source,groups,colliders,rng,scenario):
    for attempt in range(1000):
        destinations={'ROUND_BLACK_TABLE':[2.75,7.02,0],'WOODEN_BENCH':[3.4475,6.3,-90],
                      'SMALL_COFFEE_TABLE':[1.53,7.84,0],'WINDOW_CHAIR_LEFT':[.71,7.98,0],
                      'WINDOW_CHAIR_RIGHT':[2.40 if scenario=='SeatingTableUse' else 2.32,7.99,0]}
        for key,pos in destinations.items():
            if key!='WOODEN_BENCH':pos[0]+=rng.uniform(-.025,.025);pos[1]+=rng.uniform(-.025,.025)
        for chair,table in [('WINDOW_CHAIR_LEFT','SMALL_COFFEE_TABLE'),('WINDOW_CHAIR_RIGHT','ROUND_BLACK_TABLE')]:
            c=destinations[chair];t=destinations[table]
            c[2]=math.degrees(math.atan2(t[0]-c[0],-(t[1]-c[1])))+rng.uniform(-6,6)
        records={}
        for key,group in groups.items():
            x,y,yaw=destinations[key]
            oldyaw=-90 if key=='WOODEN_BENCH' else 0
            delta=pose(*group['pivot']).GetInverse()*pose(x,y,0,yaw-oldyaw)
            records[key]={'delta':rows(delta),'destination_pivot_m':[x,y,0],'yaw_delta_degrees':yaw-oldyaw,
                          'xy_displacement_m':math.dist([x,y],group['pivot'][:2]),
                          'root_world':{p:rows(mat(m)*delta) for p,m in group['original_world'].items()},'attempt':attempt+1}
        if furniture_checks(source,groups,colliders,records):return records
    raise RuntimeError('No plausible seating configuration')

def prop_plan(source,groups,colliders,records,assets,rng,scenario):
    F=PREFIX+'/Furniture/';C=PREFIX+'/ShellColliders/'
    surfaces={'round':F+'ROUND_BLACK_TABLE/CollisionProxies/RoundTop','coffee':C+'SmallCoffeeTop',
              'bedside':F+'BEDSIDE_CABINET/CollisionProxies/Top','vanity':F+'VANITY/CollisionProxies/Top',
              'luggage':F+'LUGGAGE_RACK/CollisionProxies/Top','bench':F+'WOODEN_BENCH/CollisionProxies/Seat'}
    recipes={
        'BedsideUse':[('tissue','TISSUE','bedside',[.235,5.39]),('remote','REMOTE','bedside',[.235,5.09]),('book','BOOK','bench',[3.4475,6.5]),('drink','CAN','round',None)],
        'SeatingTableUse':[('book','BOOK','coffee',None),('can','CAN','coffee',None),('remote','REMOTE','round',None),('bottle','BOTTLE','round',None)],
        'UnpackingLeaving':[('suitcase','SUITCASE','luggage',None),('bottle','BOTTLE','vanity',[3.34,2.91]),('book','BOOK','bench',[3.4475,6.55]),('remote','REMOTE','bedside',[.235,5.09])]}
    world=g.rigid_shapes(source,groups,records,colliders);placed=[];props={}
    for ident,asset,zone,fixed in recipes[scenario]:
        asset_stage=Usd.Stage.Open(str(assets[asset]));box=bounds(asset_stage,[str(asset_stage.GetDefaultPrim().GetPath())]);support=world[surfaces[zone]]
        for attempt in range(1000):
            yaw=rng.uniform(-160,160) if zone in ('round','coffee') else rng.uniform(-4,4)
            rotation=Gf.Matrix4d(1).SetRotate(Gf.Rotation(Gf.Vec3d(1,0,0),90)) if asset=='SUITCASE' else Gf.Matrix4d(1)
            rotation=rotation*pose(0,0,0,yaw)
            rotated=g.box_shape(box,rotation)
            if fixed:x,y=[v+rng.uniform(-.008,.008) for v in fixed]
            else:
                radius=support.get('radius_m',.04)*.6
                x,y=[support['center_xy'][i]+rng.uniform(-radius,radius) for i in range(2)]
            center=rotated['center_xy'];z=support['z_max']+.001-rotated['z_min']
            m=rotation*pose(x-center[0],y-center[1],z)
            shape=g.box_shape(box,m)
            if asset=='SUITCASE':shape=g.box_shape(shape['world_aabb'])
            if not g.contains(support,shape,.008):continue
            if any(g.pair(shape,b,.0001)!='PASS' for p,b in world.items() if p!=surfaces[zone]):continue
            if any(g.pair(shape,b,.008)!='PASS' for b in placed):continue
            props[ident]={'asset':asset,'asset_path':assets[asset].relative_to(ROOT).as_posix(),'asset_sha256':sha(assets[asset]),
                          'world_matrix':rows(m),'support_path':surfaces[zone],'support_zone':zone,'support_gap_m':shape['z_min']-support['z_max'],
                          'visual_state':'LYING_CLOSED_ON_RACK' if asset=='SUITCASE' else 'UPRIGHT_OR_FLAT_NATIVE'}
            placed.append(shape);break
        else:raise RuntimeError('No supported prop: '+ident)
    return props

def soft_plan(scenario,rng):
    states={'BedsideUse':{'BED_LEFT':'NeatCanonical','BED_RIGHT':'TurnedCorner'},
            'SeatingTableUse':{'BED_LEFT':'NeatCanonical','BED_RIGHT':'NeatCanonical'},
            'UnpackingLeaving':{'BED_LEFT':'SideDrape','BED_RIGHT':'TurnedCorner'}}[scenario]
    return {bed:{'state':state,'center_y':cy,'shape_seed':rng.randrange(100000),'pillow_yaws':[rng.uniform(-10,10),rng.uniform(-15,5)]}
            for bed,cy in [('BED_LEFT',6.385),('BED_RIGHT',4.155)] for state in [states[bed]]}

def derive(path, groups, manifest=None):
    s = g.derive(path, groups, None)
    s.GetRootLayer().customLayerData = {'scope': 'USED_ROOM_SCENARIO_STATIC_PREVIEW', 'soft_geometry': 'VISUAL_ONLY', 'physics': 'NOT_RUN', 'human_acceptance': 'PENDING'}
    if manifest:
        for r in manifest['furniture'].values():
            for p, m in r['root_world'].items():
                set_world(s, p, mat(m))
        for ident, r in manifest['props'].items():
            p = U.Xform.Define(s, PREFIX + '/V2Clutter/' + ident)
            p.GetPrim().GetReferences().AddReference(relative(ROOT / r['asset_path'], path))
            set_world(s, str(p.GetPath()), mat(r['world_matrix']))
    s.GetRootLayer().Save()
    return s

def signature(s):
    return {str(p.GetPath()):{'type':p.GetTypeName(),'attrs':{a.GetName():str(a.Get()) for a in p.GetAttributes()},'rels':{r.GetName():[str(t) for t in r.GetTargets()] for r in p.GetRelationships()}} for p in prims(s)}

def validate(path,source,groups,colliders,m):
    s=Usd.Stage.Open(str(path));assert s and not s.GetCompositionErrors()
    layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(path));assert not unresolved
    assert U.GetStageUpAxis(s)=='Z' and U.GetStageMetersPerUnit(s)==1 and str(s.GetDefaultPrim().GetPath())==PREFIX
    cache=U.XformCache();joints=[p for p in prims(source) if p.IsA(P.Joint)];assert len(joints)==8
    for p in joints:
        q=s.GetPrimAtPath(p.GetPath())
        for a in p.GetAttributes():assert a.Get()==q.GetAttribute(a.GetName()).Get()
        for r in p.GetRelationships():assert r.GetTargets()==q.GetRelationship(r.GetName()).GetTargets()
    report={'status':'STATIC_PREVIEW_PASS','sha256':sha(path),'unresolved':[],'joint_properties_unchanged':True}
    if m:
        records=m['furniture'];assert furniture_checks(source,groups,colliders,records)
        for r in records.values():
            for p,world in r['root_world'].items():assert max(abs(cache.GetLocalToWorldTransform(s.GetPrimAtPath(p))[i][j]-world[i][j]) for i in range(4) for j in range(4))<1e-8
        assert records['WOODEN_BENCH']['xy_displacement_m']==0 and mat(records['WOODEN_BENCH']['delta'])==Gf.Matrix4d(1)
        world=g.rigid_shapes(source,groups,records,colliders);prop_shapes=[]
        for ident,r in m['props'].items():
            st=Usd.Stage.Open(str(ROOT/r['asset_path']));bb=bounds(st,[str(st.GetDefaultPrim().GetPath())]);p=s.GetPrimAtPath(PREFIX+'/V2Clutter/'+ident)
            actual=cache.GetLocalToWorldTransform(p);assert rows(actual)==r['world_matrix']
            shape=g.box_shape(bb,actual);support=world[r['support_path']]
            if r['asset']=='SUITCASE':shape=g.box_shape(shape['world_aabb'])
            assert g.contains(support,shape,.0079) and abs(shape['z_min']-support['z_max']-.001)<1e-5
            assert all(g.pair(shape,b,.0001)=='PASS' for p0,b in world.items() if p0!=r['support_path'])
            assert all(g.pair(shape,b,.0079)=='PASS' for b in prop_shapes);prop_shapes.append(shape)
        soft={}
        for p in prims(s):
            if str(p.GetPath()).startswith(PREFIX+'/V2Soft/') and p.IsA(U.Mesh):
                pts=U.Mesh(p).GetPointsAttr().Get();assert all(all(math.isfinite(x) for x in v) for v in pts)
                assert min(v[2] for v in pts)>.20
                counts=U.Mesh(p).GetFaceVertexCountsAttr().Get();idx=U.Mesh(p).GetFaceVertexIndicesAttr().Get()
                assert sum(counts)==len(idx) and max(idx)<len(pts)
                # Closure: each undirected mesh edge belongs to two faces.
                edges={};offset=0
                for n in counts:
                    face=idx[offset:offset+n];offset+=n
                    for a,b in zip(face,list(face[1:])+[face[0]]):
                        edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
                assert all(n==2 for n in edges.values())
                soft[str(p.GetPath())]={'vertices':len(pts),'closed_edges':True,'minimum_z':min(v[2] for v in pts)}
        report.update(relations=relation(records),bench_fixed=True,reserved_strip='PROTOTYPE_AVOIDANCE_PASS',soft_meshes=soft)
    else:
        src=U.XformCache()
        for p in prims(source):
            if U.Xformable(p):assert cache.GetLocalToWorldTransform(s.GetPrimAtPath(p.GetPath()))==src.GetLocalToWorldTransform(p)
        report['clean_reset']='PASS'
    return report
