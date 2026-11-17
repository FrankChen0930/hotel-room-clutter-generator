"""Pure Scenario/Level planner. No USD, filesystem, global RNG or seed recipes."""
from .contracts import validate_contract
from .identity import rng_for, stable_request_id, validate_seed
from .room import Inputs


def plan_requests(inputs: Inputs, seed: int, scenario: str, level: str) -> dict:
    validate_seed(seed)
    policy=validate_contract(inputs.policy,'Policy');validate_contract(inputs.catalog,'Catalog')
    if scenario not in policy['scenarios']:raise ValueError('UNKNOWN_SCENARIO')
    if level not in policy['levels']:raise ValueError('UNKNOWN_LEVEL')
    config=policy['scenarios'][scenario];target=policy['levels'][level]
    lo,hi=target['count_ranges'][scenario];q=rng_for(seed,'count/'+scenario,'scene').random()
    count=lo+int(q*(hi-lo+1));room_id=inputs.profile['profile_id']
    eligible_categories=set(config['eligible_categories'])&set(target.get('eligible_categories',config['eligible_categories']))
    entries=sorted([e for e in inputs.catalog['entries'] if room_id in e.get('room_ids',[room_id])
                    and e['category'] in eligible_categories],key=lambda e:e['asset_id'])
    used_native=set();ordinals={};requests=[]
    supports=[s for s in inputs.profile['supports'] if set(s['tags'])&set(config['allowed_support_tags'])]
    if not supports:raise ValueError('NO_ELIGIBLE_SUPPORT')
    def add(role):
        category=role['category'];key=(role['role'],category);ordinal=ordinals.get(key,0)
        if ordinal>=role.get('max_instances',count):return False
        request_id=stable_request_id(*key,ordinal)
        def eligible_states(asset):
            return sorted([s for s in asset['states'] if set(s['allowed_pose_tags'])&set(target['allowed_pose_tags'])
                and s['state_id'] in target.get('allowed_states',{}).get(category,[s['state_id']])],key=lambda s:s['state_id'])
        eligible=[e for e in entries if e['category']==category and e['asset_id'] not in used_native and eligible_states(e)]
        if not eligible:return False
        asset=eligible[rng_for(seed,'asset/'+scenario,request_id).randrange(len(eligible))]
        states=eligible_states(asset)
        if not states:return False
        state=states[rng_for(seed,'state/'+scenario,request_id).randrange(len(states))]
        if asset['origin']=='native':used_native.add(asset['asset_id'])
        ordinals[key]=ordinal+1
        requests.append(dict(request_id=request_id,role=role['role'],category=category,asset_id=asset['asset_id'],
            state_id=state['state_id'],origin=asset['origin'],source_object_id=asset.get('source_object_id'),
            semantic_state=dict(role['semantics']),allowed_support_ids=sorted(s['support_id'] for s in supports),
            allowed_pose_tags=sorted(set(state['allowed_pose_tags'])&set(target['allowed_pose_tags'])),required=True,priority=role['priority']))
        return True
    roles=config['roles']
    required_categories=list(dict.fromkeys([*config['required_categories'],*target.get('extra_required_categories',[])]))
    for category in required_categories:
        options=[r for r in roles if r['category']==category]
        if not options or not add(options[0]):raise ValueError('REQUIRED_CATEGORY_UNAVAILABLE: '+category)
    if len(requests)>count:raise ValueError('REQUIRED_QUOTA_EXCEEDS_COUNT')
    # Bounded by the requested count and role count; exhausted native entries are ineligible.
    while len(requests)<count:
        prior=len(requests)
        for role in roles:
            if len(requests)==count:break
            add(role)
        if len(requests)==prior:raise ValueError('COUNT_TARGET_UNSATISFIABLE')
    return dict(schema_version='1.0',seed=seed,scenario=scenario,level=level,room_id=room_id,
        requests=sorted(requests,key=lambda r:(r['priority'],r['request_id'])),
        targets=dict(count=count,count_range=[lo,hi],coverage=target['coverage'],spread=target['spread'],
                     state_proportions=target['state_proportions'],required_categories=required_categories,
                     required_state_counts=target.get('required_state_counts',{})),
        budgets=dict(policy['budgets']),assumptions=policy['assumptions'])
