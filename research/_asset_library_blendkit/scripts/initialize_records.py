"""One-time first-batch records from reviewed official pages; never downloads models."""
from pathlib import Path
import sys
from library import ROOT, read, write, sha

def main():
    target=ROOT/'registry/assets.json'
    if target.exists(): raise ValueError('REGISTRY_ALREADY_EXISTS')
    rows=[
        ('755a9a16-d738-44ab-9ab6-07d35db05e47','Folded Towel','Rex Hans','towel','folded_towel','FREE','Royalty Free',7.0,8256,'bathroom_use',None),
        ('a71b4afd-25d4-49d8-8aa0-9eb6d8f45034','Towel Crumpled','Silas Fuchs','towel','crumpled_towel','FREE','Royalty Free',6.6,2601,'checkout_traces',None),
        ('83fcc23b-e4b5-459a-b610-d9317aaa7638','Toothpaste','Mesk911','toiletry','toothpaste_tube','FREE','Royalty Free',6.5,782,'bathroom_use',None),
        ('2a6fba98-cd9b-4455-a2f7-ca32eacffeb0','Oralb Toothpaste','GL3D Gabriela Linhares','toiletry','toothpaste_box','FREE','Royalty Free',7.0,174,'bathroom_use',None),
        ('557705f1-ef41-4a8c-9238-4a05f2cec153','Backpack','ali alipour','bag','travel_backpack','FULL_PLAN','Royalty Free',9.5,2070,'arrival_unpacking',None),
        ('1bd7f567-f900-4ca7-9929-1b6631409c96','Towels','GL3D Gabriela Linhares','towel','folded_towel_scan','FULL_PLAN','Royalty Free',9.0,143996,'bathroom_use',None),
        ('b147eaa3-47f4-4882-82b4-e338d8d84bb1','Laptop',None,'electronics','open_laptop','FREE','UNKNOWN',None,None,'desk_charging',None),
        ('4c59a321-3330-4532-af49-3d0cbbb80bff','Cosmetic Tubes Studio Display Scene',None,'scene','product_display','FULL_PLAN','Royalty Free',6.0,12947,'bathroom_use','SCENE_DISPLAY_NOT_INDEPENDENT_GUEST_PROP'),
    ]
    assets=[]
    for aid,name,author,category,family,plan,license,quality,poly,situation,reject in rows:
        blockers=[] if reject else ['OFFICIAL_ACQUISITION_UNAVAILABLE','EXTRACTABLE_USD_RIGHTS_UNCLEARED']
        if plan=='FULL_PLAN' and not reject: blockers.append('PAID_PLAN_NOT_AUTHORIZED')
        if license=='UNKNOWN': blockers.append('DETAIL_PAGE_LICENSE_AUTHOR_NOT_VERIFIED')
        assets.append(dict(asset_id='bk-'+aid,name=name,author=author,category=category,
            situations=[situation],appearance_family=family,geometry_identity=None,variant_of=None,
            state_id='default',status='REJECTED' if reject else 'BLOCKED',last_completed_stage='DISCOVERED',
            source=dict(provider='Blendkit',asset_base_id=aid,version_id=None,
                url='https://www.blendkit.com/asset-gallery-detail/'+aid+'/',
                metadata_checked_date='2026-11-15',metadata_scope='Official public page, not downloaded add-on metadata',
                plan=plan,original_file=None,acquisition_method=None,receipt=None),
            rights=dict(license=license,license_url='https://www.blendkit.com/docs/licenses/',
                terms_url='https://www.blendkit.com/terms-and-conditions-2026/',
                internal_use=True if license=='Royalty Free' else None,
                redistribution=None,extractable_usd=None,requires_user_acquisition=True,
                decision='PENDING_EXTRACTABLE_USD_TERMS',decision_evidence=None),
            discovery_quality=dict(site_quality_score=quality,site_polygon_count=poly,visual_acceptance='NOT_REVIEWED',
                uniqueness='SOURCE_ID_DISTINCT_GEOMETRY_NOT_VERIFIED',relevance='Guest prop candidate' if not reject else 'Unsuited studio scene'),
            dimensions_m=None,physics=dict(mode='UNQUALIFIED',mass_kg=None,collision_proxy=None),
            usd={},evidence={},blockers=blockers,rejection_reason=reject))
    write(target,dict(schema_version='1.0',assets=assets))
    situations={
        'arrival_unpacking':dict(activity='Guest opens luggage and sorts belongings',zones=['local_floor','bench','chair'],queries=['carry on suitcase','open suitcase','duffel bag','backpack','handbag','packing cube']),
        'rest_reading':dict(activity='Guest rests, reads and leaves items nearby',zones=['bed_s0','chair','bedside','local_floor'],queries=['paperback book','magazine','reading glasses','headphones','travel pillow']),
        'desk_charging':dict(activity='Laptop work and charging personal electronics',zones=['desk','bedside','local_floor'],queries=['laptop','smartphone','charger','USB cable','power bank','earbuds case','notebook','pen']),
        'changing_clothes':dict(activity='Changing for outings and sorting clothes',zones=['bed_s0','chair','local_floor','bench'],queries=['crumpled t-shirt','folded jeans','jacket','socks','cap','sneaker','slipper']),
        'food_drink':dict(activity='Eating snacks and drinking in room',zones=['desk','minibar','bedside','local_floor'],queries=['takeaway cup','water bottle','paper bag','snack wrapper','food container','drink can']),
        'bathroom_use':dict(activity='Washing and personal grooming',zones=['bathroom_support','bench','bed_s0'],queries=['toothbrush','toothpaste','shampoo bottle','cosmetic pouch','hairbrush','razor','folded towel','crumpled towel']),
        'stayover_personal':dict(activity='Personal belongings remain during stay',zones=['desk','bed_s0','bench','chair','local_floor'],queries=['passport','travel document','key card','watch','wallet','shopping bag']),
        'checkout_traces':dict(activity='Guest has left; housekeeping sorts traces',zones=['local_floor','bed_s0','desk','bathroom_support'],queries=['used tissue','crumpled paper','empty carton','discarded clothes','used towel'])}
    write(ROOT/'config/scenarios.json',dict(scope='Search intents, not candidates or category quotas; zones require room-specific validation',situations=situations))
    write(ROOT/'config/environment.json',dict(blender='C:/Program Files/Blender Foundation/Blender 5.2/blender.exe',isaac_root='C:/isaac_sim',python='C:/isaac_sim/kit/python/python.exe',
        profile=str(ROOT/'blender_profile'),addon_status='NOT_FOUND_IN_CHECKED_LOCATIONS',login='NOT_YET_NEEDED',
        addon_official_url='https://www.blendkit.com/get-blendkit/',acquisition='BLOCKED_LOCAL_NETWORK',
        batch_acquisition='NOT_ESTABLISHED_USE_OFFICIAL_PER_ASSET_UI',native_runtime='NOT_YET_PROBED'))
    # Snapshot only the protected project's relevant source/config/manifests, without writing into it.
    workspace=ROOT.parent; protected=[]
    for folder in ('common_core','_common_core_runs/quality_experiments/scene_quality_v02_20261114T153126Z'):
        for p in (workspace/folder).rglob('*'):
            if p.is_file() and p.suffix in {'.py','.json','.md','.csv','.html'} and not any(x in p.parts for x in ('.git','__pycache__','cache','texturecache','shadercache','drivercache')):
                protected.append(p)
    for p in (workspace/'_hotel705_reference/release_v1.0.0').rglob('*'):
        if p.is_file() and p.suffix in {'.usd','.usda','.usdc','.blend','.json'}: protected.append(p)
    write(ROOT/'reports/protected_before.json',dict(scope='Common Core code/config and V0.2 code/config/receipts; original Hotel reference scene and blend files',files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(set(protected))]))
    print('Registered',len(assets),'real page identities; protected',len(set(protected)),'files')

if __name__=='__main__':main()
