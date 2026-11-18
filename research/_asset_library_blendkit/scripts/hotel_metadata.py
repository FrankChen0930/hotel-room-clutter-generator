"""Hotel semantics and robotics candidacy; shape appearance never grants physics qualification."""
ROBOTICS={'scene_only','perception_candidate','manipulation_candidate','soft_object_research_candidate'}

def choose_local_subset(records,seed,maximum=5):
    """Bound room density independently of library size; poses still require Core validation."""
    import random
    if not 1<=maximum<=8:raise ValueError('INVALID_ROOM_NEW_ASSET_LIMIT')
    rng=random.Random(seed);pool=sorted(records,key=lambda a:a['asset_id']);selected=[]
    for category in ('luggage','bag','clothing','footwear'):
        choices=[a for a in pool if a['category']==category]
        if choices and len(selected)<maximum:selected.append(rng.choice(choices))
    remainder=[a for a in pool if a not in selected and a['category'] not in {'luggage','bag','clothing','footwear'}]
    rng.shuffle(remainder)
    selected.extend(remainder[:maximum-len(selected)])
    return selected
REGIONS={
 'bag':['floor','bench','chair_area','bedside'], 'luggage':['floor','bench','chair_area'],
 'clothing':['floor','chair','bench','bed_adjacent'], 'footwear':['floor','bedside','chair_area'],
 'electronics':['bedside','table','bench'], 'toiletry':['cabinet','minibar','bench'],
 'towel':['floor','bench','chair','bed_adjacent'], 'paper':['bedside','bench','table','floor'],
 'book':['bedside','chair','table'], 'food':['table','minibar','floor'],
 'personal':['bedside','table','bench','chair'], 'scene':[]}

def enrich(a):
    category=a['category'];soft=category in {'bag','clothing','towel'} or (category=='luggage' and any(x in a['name'].lower() for x in ('duffel','fabric','soft'))) or (category=='toiletry' and any(x in a['name'].lower() for x in ('toothpaste','squeezable','pouch','tube')))
    accepted=a.get('local_qualification',{}).get('outcome')=='PASS'
    a['semantic_category']=category
    a['hotel_use_scenarios']=list(a.get('situations',[]))
    a['possible_placement_regions']=list(a.get('batch_job',{}).get('regions') or REGIONS.get(category,['floor','bench']))
    a['geometry_family']=a.get('geometry_family') or ('travel_backpack_fixed_scan' if category=='bag' else category+'_fixed_form')
    a['visual_family']=a.get('appearance_family','pending_visual_review')
    a['object_form']='S0-like' if category=='towel' or a.get('state_id','').startswith('s0_') else 'soft-like' if soft else 'rigid'
    a['physics_qualification']=a.get('physics',{}).get('mode','UNQUALIFIED').lower()
    a['physical_tags']=[a['object_form']]+(['static_only'] if a.get('physics',{}).get('mode')=='STATIC_ONLY' else ['physics_unqualified'])
    a['robotics_relevance']='soft_object_research_candidate' if category in {'clothing','towel'} else 'perception_candidate' if category!='scene' else 'scene_only'
    a['robotics_note']='Fixed mesh only; soft-like but not physically solved. No deformation/grasp/dynamic qualification.' if soft else 'Robotics label is candidacy only; no manipulation or dynamics qualification inferred.'
    a['deformation_solved']=False
    rejected=a['status']=='REJECTED'
    a['quality_decision']='rejected' if rejected else 'accepted' if accepted else 'blocked'
    a['quality_reason']=a.get('rejection_reason') if rejected else 'Actual local visual/static/native/support/replay acceptance; rights tracked separately' if accepted else 'Acquisition, conversion or actual visual/technical review incomplete'
    a['hotel_suitability']=dict(decision='rejected' if rejected else 'accepted' if accepted else 'candidate',
        reason='Guest/housekeeping situation relevance; possible regions are semantic suggestions and require actual room support validation' if not rejected else a.get('rejection_reason'))
    return a
