"""Cross-field rules for the four V1 JSON contracts; no USD dependency."""
import math
from pathlib import PurePosixPath, PureWindowsPath
import re
from .identity import validate_seed

REQUIRED = {
    'RoomProfile': 'profile_id profile_version source coordinates supports forbidden_regions source_objects override_allowlist test_freeze cameras provenance'.split(),
    'Catalog': 'catalog_id version entries'.split(),
    'Policy': 'policy_id version assumptions scenarios levels budgets'.split(),
    'Manifest': 'generator_version run_id attempt_id parent_attempt_id inputs environment requests targets achieved objects scene evidence_refs failure_refs attempt_lineage limits'.split(),
}


def typed(value, kind):
    if type(value) is not kind: raise ValueError('TYPE_' + kind.__name__)


def fields(data, keys):
    typed(data, dict)
    for key in keys:
        if key not in data: raise ValueError('MISSING_FIELD: ' + key)


def text(value):
    if not isinstance(value, str) or not value: raise ValueError('TYPE_NONEMPTY_STRING')


def finite(value):
    if isinstance(value, float) and not math.isfinite(value): raise ValueError('NONFINITE')
    if isinstance(value, dict):
        for child in value.values(): finite(child)
    elif isinstance(value, list):
        for child in value: finite(child)


def sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value): raise ValueError('SHA256')


def prim(value):
    if not isinstance(value, str) or not value.startswith('/') or any(s in ('', '.', '..') for s in value[1:].split('/')):
        raise ValueError('PRIM_PATH')


def locator(value):
    fields(value, ['mount', 'path']); text(value['mount']); text(value['path'])
    path = value['path']
    if (PureWindowsPath(path).drive or PureWindowsPath(path).is_absolute() or PurePosixPath(path).is_absolute()
            or ':' in path or '\\' in path or any(p in ('', '.', '..') for p in path.split('/'))):
        raise ValueError('SOURCE_PATH')


def matrix(value):
    if not isinstance(value, list) or len(value) != 4 or any(not isinstance(row, list) or len(row) != 4
            or any(type(x) not in (int, float) for x in row) for row in value): raise ValueError('MATRIX_4X4')
    finite(value)
    if any(abs(value[i][3]) > 1e-12 for i in range(3)) or abs(value[3][3]-1) > 1e-12:
        raise ValueError('MATRIX_ROW_AFFINE')


def unique(items, key):
    typed(items, list); seen = set()
    for item in items:
        fields(item, [key]); text(item[key])
        if item[key] in seen: raise ValueError('DUPLICATE_ID: ' + item[key])
        seen.add(item[key])


def profile(data):
    source = data['source']; fields(source, ['root_prim','sha256','closure_ref','closure_sha256'])
    locator(source); prim(source['root_prim']); sha(source['sha256']); sha(source['closure_sha256'])
    coord=data['coordinates'];fields(coord,['meters_per_unit','up_axis','to_common']);matrix(coord['to_common'])
    if type(coord['meters_per_unit']) not in (float,int) or coord['meters_per_unit']<=0 or coord['up_axis'] not in ('X','Y','Z'):
        raise ValueError('COORDINATES')
    unique(data['supports'],'support_id');unique(data['source_objects'],'object_id');typed(data['override_allowlist'],list)
    for support in data['supports']:
        fields(support,['prim','collider','kind','local_frame','allowed_region','edge_margin_m','tags'])
        prim(support['prim']);prim(support['collider']);matrix(support['local_frame'])
        if support['kind'] not in ('mesh_top','primitive_top','floor_region'):raise ValueError('SUPPORT_KIND')
        if type(support['edge_margin_m']) not in (float,int) or support['edge_margin_m']<0:raise ValueError('SUPPORT_MARGIN')
    for obj in data['source_objects']:
        fields(obj,['prim','mobility','allowed_operations']);prim(obj['prim']);typed(obj['allowed_operations'],list)
        if obj['mobility'] not in ('FIXED','MOVABLE','ARTICULATED'):raise ValueError('MOBILITY')
    for override in data['override_allowlist']:
        fields(override,['prim','attributes']);prim(override['prim']);typed(override['attributes'],list);p=override['prim']
        for obj in data['source_objects']:
            fixed=obj['prim']
            if obj['mobility']=='FIXED' and (p==fixed or p.startswith(fixed+'/') or fixed.startswith(p+'/')):
                raise ValueError('FIXED_OBJECT_OVERRIDE: '+p)
        owners=[o for o in data['source_objects'] if o['prim']==p and o['mobility']=='MOVABLE']
        if not owners:raise ValueError('OVERRIDE_NOT_MOVABLE: '+p)
        if any(a not in owners[0]['allowed_operations'] for a in override['attributes']):raise ValueError('OVERRIDE_ATTRIBUTE_NOT_ALLOWED')
    for key,kind in [('forbidden_regions',list),('test_freeze',dict),('cameras',list),('provenance',dict)]:typed(data[key],kind)


def catalog(data):
    unique(data['entries'],'asset_id')
    for entry in data['entries']:
        fields(entry,'version category origin source_locator dependency_hashes root_prim dimensions provenance license_scope states'.split())
        if 'asset_globally_physics_pass' in entry:raise ValueError('GLOBAL_QUALIFICATION_FORBIDDEN')
        if entry['origin'] not in ('native','external'):raise ValueError('ASSET_ORIGIN')
        (locator if entry['origin']=='external' else prim)(entry['source_locator'])
        prim(entry['root_prim']);text(entry['license_scope']);dims=entry['dimensions']
        if not isinstance(dims,list) or len(dims)!=3 or any(type(v) not in (float,int) or v<=0 for v in dims):raise ValueError('ASSET_DIMENSIONS')
        unique(entry['states'],'state_id')
        if not entry['states']:raise ValueError('ASSET_STATES_EMPTY')
        for state in entry['states']:
            fields(state,'version usd_locator_or_native_prim sha256 units up_axis pivot alignment visual_bounds footprint support_envelope allowed_pose_tags acceptance_refs physics_proxy'.split())
            sha(state['sha256']);matrix(state['alignment'])
            (locator if entry['origin']=='external' else prim)(state['usd_locator_or_native_prim'])
            proxy=state['physics_proxy'];fields(proxy,['kind','capability','shape_paths','geometry_hash']);sha(proxy['geometry_hash'])
            if proxy['kind'] not in ('box','cylinder','convex','compound','none'):raise ValueError('PROXY_KIND')
            if proxy['capability'] not in ('STATIC_ONLY','DYNAMIC_CANDIDATE'):raise ValueError('PROXY_CAPABILITY')
            if proxy['kind']=='none' and proxy['capability']!='STATIC_ONLY':raise ValueError('PROXY_NONE_DYNAMIC')
            typed(proxy['shape_paths'],list)
            if proxy['kind']!='none':
                fields(proxy,['relative_transforms','mass','inertia','material_refs','provenance'])
                if not proxy['shape_paths']:raise ValueError('PROXY_SHAPES_EMPTY')


def policy(data):
    typed(data['scenarios'],dict);typed(data['levels'],dict)
    if not {'STAYOVER','CHECKOUT'} <= data['scenarios'].keys():raise ValueError('SCENARIOS_REQUIRED')
    for scenario in data['scenarios'].values():
        fields(scenario,['roles','eligible_categories','ownership','action','required_categories','allowed_support_tags'])
        if scenario['ownership'] in ('guest','unknown') and scenario['action']=='discard':raise ValueError('GUEST_DISCARD_FORBIDDEN')
    fields(data['levels'],['low','medium','high'])
    for scenario in data['scenarios']:
        previous=-1
        for level in ['low','medium','high']:
            fields(data['levels'][level],['count_ranges','coverage','spread','state_proportions','allowed_pose_tags'])
            ranges=data['levels'][level]['count_ranges'];fields(ranges,[scenario]);interval=ranges[scenario]
            if not isinstance(interval,list) or len(interval)!=2 or any(type(x) is not int or x<0 for x in interval) or interval[0]>interval[1]:raise ValueError('COUNT_RANGE')
            if interval[0]<=previous:raise ValueError('COUNT_RANGE_OVERLAP')
            previous=interval[1]
    caps=dict(max_supports=3,samples_per_support=800,repair_passes=1,max_samples_per_request=4800,native_retries=1)
    fields(data['budgets'],caps)
    for key,cap in caps.items():
        value=data['budgets'][key]
        if type(value) is not int or not (0 if key in ('repair_passes','native_retries') else 1)<=value<=cap:raise ValueError('BUDGET: '+key)
    if data.get('release_frozen'):
        fields(data,['metrics']);fields(data['metrics'],['version','catalog_hash','rooms','calibration']);sha(data['metrics']['catalog_hash'])
        for room in data['metrics']['rooms'].values():
            fields(room,['profile_hash','denominator_m2','coverage']);sha(room['profile_hash'])
            if type(room['denominator_m2']) not in (float,int) or room['denominator_m2']<=0:raise ValueError('FROZEN_MASK_AREA')
            for scenario in data['scenarios']:
                for level in ['low','medium','high']:
                    interval=room['coverage'][scenario][level]
                    if not isinstance(interval,list) or len(interval)!=2 or not 0<=interval[0]<=interval[1]<=1:raise ValueError('FROZEN_COVERAGE_INTERVAL')


def manifest(data):
    fields(data['inputs'],['seed','scenario','level','code_hash','profile_hash','catalog_hash','policy_hash','source_closure_hash'])
    validate_seed(data['inputs']['seed'])
    for key in ['code_hash','profile_hash','catalog_hash','policy_hash','source_closure_hash']:sha(data['inputs'][key])
    unique(data['objects'],'instance_id')
    for obj in data['objects']:
        fields(obj,'request_id asset_id state_sha256 origin source_object_id native_prim before after effective'.split())
        if {'soft','refined_bedding'} & obj.keys():raise ValueError('AMBIGUOUS_STATE')
        sha(obj['state_sha256']);fields(obj['before'],['exists'])
        if obj['origin']=='native':
            if not obj['source_object_id'] or not obj['native_prim'] or obj['before']['exists'] is not True:raise ValueError('NATIVE_MAPPING')
            prim(obj['native_prim']);fields(obj['before'],['world_matrix']);matrix(obj['before']['world_matrix'])
        elif obj['origin']=='external':
            if obj['before']['exists'] is not False or 'world_matrix' in obj['before']:raise ValueError('EXTERNAL_BEFORE')
        else:raise ValueError('ASSET_ORIGIN')
        for key in ['after','effective']:
            fields(obj[key],['world_matrix','state_id','support_id','semantic_state','body_mode']);matrix(obj[key]['world_matrix'])
    fields(data['scene'],['locator','sha256','state_digest','dependencies'])
    locator(data['scene']['locator']);sha(data['scene']['sha256']);sha(data['scene']['state_digest']);typed(data['evidence_refs'],list)
    for ref in data['evidence_refs']:
        fields(ref,['kind','uri','sha256','execution','outcome','scope','target_state_digest','producer_identity'])
        sha(ref['sha256']);sha(ref['target_state_digest'])
        if ref['execution'] not in ('NOT_RUN','EXECUTED','RECORDED') or ref['outcome'] not in ('PASS','FAIL','UNKNOWN','NOT_APPLICABLE'):raise ValueError('EVIDENCE_STATUS')
        if ref['execution']=='NOT_RUN' and ref['outcome']=='PASS':raise ValueError('EVIDENCE_NOT_RUN_PASS')


VALIDATORS={'RoomProfile':profile,'Catalog':catalog,'Policy':policy,'Manifest':manifest}
