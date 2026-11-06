import sys,json,copy,types,random,math
from pathlib import Path
from types import SimpleNamespace
from common import *
import iterate as gen
import generate as g
import bedding_helpers as b
a=SimpleNamespace(ROOT=ROOT,PREFIX=PREFIX,sha=sha,read=read)
HERE=CONFIG_DIR
POLICY=read(HERE/'task_policy.json')
SOFT=read(HERE/'soft_variation.json')

def metadata(asset,mode):
    personal=asset in ('BOOK','SUITCASE') or (asset=='BOTTLE' and mode=='STAYOVER_CLEANING')
    empty=mode=='CHECKOUT_CLEANING' and asset in ('CAN','BOTTLE')
    return {'category':'PERSONAL_BELONGING' if personal else 'DECLARED_TRASH' if empty else 'HOTEL_AMENITY','ownership':'GUEST' if personal else 'DECLARED_DISCARDED_CONSUMABLE' if empty else 'HOTEL_ASSUMED_RESEARCH','state':'EMPTY_CONTENTS_DECLARED_SYNTHETICALLY' if empty else 'IN_USE_OR_CLOSED','state_evidence':'EXPLICIT_SYNTHETIC_AUTHOR_DECLARATION' if empty else 'SYNTHETIC_SCENARIO_ROLE_NOT_VERIFIED_HOTEL_INVENTORY','robot_action_policy':'DO_NOT_TOUCH' if personal else 'NEEDS_HUMAN_CONFIRMATION','action_candidate':'NONE' if personal else 'COLLECT_DECLARED_WASTE' if empty else 'REPOSITION_HOTEL_AMENITY','task_mode':mode,'physics_state_scope':'NEW_POSE_AND_STATE_REQUIRES_EVIDENCE'}

def task_plan(seed,mode,source,groups,colliders,assets,furniture):
    policy=POLICY['modes'][mode];rng=random.Random(seed+({'CHECKOUT_CLEANING':17000,'STAYOVER_CLEANING':27000}[mode]))
    props=gen.prop_plan(source,groups,colliders,furniture,assets,rng,policy['base_prop_recipe'])
    props={key:{**v,'task_metadata':metadata(v['asset'],mode)} for key,v in props.items() if key not in policy['exclude']}
    soft=gen.soft_plan('SeatingTableUse',rng);pair=rng.choice(policy['soft_pairs'])
    for bed,state in zip(('BED_LEFT','BED_RIGHT'),pair):soft[bed]['state']=state
    return {'seed':seed,'scenario':mode,'task_mode':mode,'research_authority':POLICY['authority'],'parameters':gen.CONFIG,'furniture':copy.deepcopy(furniture),'relations':gen.relation(furniture),'props':props,'soft':soft,'status':'STATIC_PREVIEW','soft_status':'VISUAL_ONLY','physics':'NOT_RUN','human_acceptance':'PENDING','policy_sha256':a.sha(HERE/'task_policy.json')}

def bedding(path,seed,mode,states,m):
    # Existing overlay makes adopted mesh references. Only scene-local state/pose
    # overrides follow; assets and old library are never edited.
    fn=types.FunctionType(b.overlay.__code__,{**b.overlay.__globals__,'PREVIOUS':path.parents[2]/'generated'/mode})
    bm=fn(path,seed,states);s=Usd.Stage.Open(str(path));rng=random.Random(seed+(3100 if mode=='CHECKOUT_CLEANING' else 7300));instances=[]
    for bed,r in m['soft'].items():
        parent=a.PREFIX+'/RefinedBedding/'+bed;cy=r['center_y'];support=a.PREFIX+'/Furniture/'+bed+'/Visual/Mattress';ss=g.box_shape(bounds(s,[support]));placed=[]
        if r['state']!='NeatCanonical':
            p=parent+'/Duvet';flip=r['state']=='TurnedCorner' and bool(rng.randrange(2));mm=Gf.Matrix4d(1).SetScale(Gf.Vec3d(1,-1 if flip else 1,1))*pose(0,cy,0);set_world(s,p,mm)
            instances.append({'path':p,'state':r['state'],'asset_path':states[r['state']].relative_to(a.ROOT).as_posix(),'asset_sha256':a.sha(states[r['state']]),'world_matrix':rows(mm),'parameters':{'fold_mirrored_y':flip,'no_translation_jitter':True},'qualification':'VISUAL_ONLY','support':support})
        for i,offset in enumerate(SOFT['pillow']['center_y_offsets_m']):
            state='CompressedPillow' if rng.random()<POLICY['modes'][mode]['pillow_compression_probability'] else 'NeatPillow';ast=Usd.Stage.Open(str(states[state]));bb=bounds(ast,[str(ast.GetDefaultPrim().GetPath())])
            for attempt in range(SOFT['pillow']['attempts_max']):
                mm=pose(rng.uniform(*SOFT['pillow']['center_x_range_m']),cy+offset,ss['z_max']+.001-bb['min'][2],rng.uniform(*SOFT['pillow']['yaw_range_deg']));shape=g.box_shape(bb,mm)
                if g.contains(ss,shape,.005) and all(g.pair(shape,v,.001)=='PASS' for v in placed):break
            else:raise RuntimeError('PILLOW_BOUNDED_SUPPORT_REJECTION')
            p=parent+'/Pillow'+str(i);s.RemovePrim(p);xf=U.Xform.Define(s,p);xf.GetPrim().GetReferences().AddReference(relative(states[state],path));set_world(s,p,mm);placed.append(shape)
            instances.append({'path':p,'state':state,'asset_path':states[state].relative_to(a.ROOT).as_posix(),'asset_sha256':a.sha(states[state]),'world_matrix':rows(mm),'support':support,'parameters':{'bounded_attempt':attempt+1,'compression_is_mesh_state_not_rotation':True,'stacked_contact_override':'REMOVED_IN_NEW_SCENE_LAYER'},'qualification':'VISUAL_ONLY'})
    bm['instances']=instances;bm['variation_policy_sha256']=a.sha(HERE/'soft_variation.json');s.GetRootLayer().Save();return bm
