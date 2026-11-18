"""Select the two adopted towel mesh states; do not generate or deform assets."""
from pathlib import Path
import argparse
import json
import sys
CODE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(CODE))
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Usd,UsdGeom,UsdUtils
from common_core.contracts import load_json,validate_contract,verify_source
from common_core.identity import sha256_file
from common_core.manifest import write_json_new
from common_core.paths import guard_new_output
from common_core.room import bounds,rows,geometry_signature
from pxr import Gf


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=guard_new_output(args.output);out.mkdir(parents=True)
    root=CODE.parent/'YAZHI-TWIN';decision=root/'experiments/phase_v2_room_clutter/task_quality/outputs/run_20261105T084007032045Z/selective_acceptance.json'
    adopted=load_json(decision)['components'];lock=load_json(CODE/'config/source_lock.json');catalog=load_json(CODE/'config/catalog.json')
    if any(e['asset_id']=='s0_towel' for e in catalog['entries']):raise ValueError('S0_SELECTION_ALREADY_EXISTS')
    states=[];proofs=[];assets={(a['mount'],a['path']):a for a in lock.get('assets',[])}
    for state_id,component,which in [('folded','FoldedChairTowel','previous'),('loose','LooseTowel','refined')]:
        item=adopted[component]
        if item['decision'] not in ('KEEP_PREVIOUS','ADOPT_REFINED'):raise ValueError('S0_NOT_ADOPTED')
        source=item[which];path=root/source['path'];verify_source(path,source['sha256']);stage=Usd.Stage.Open(str(path));prim=stage.GetDefaultPrim()
        if UsdGeom.GetStageMetersPerUnit(stage)!=1 or UsdGeom.GetStageUpAxis(stage)!='Z':raise ValueError('S0_UNSUPPORTED_UNITS')
        bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy']);visual=bounds(prim,bbox)
        location=dict(mount='room_yazhi',path=source['path']);layers,dependencies,unresolved=UsdUtils.ComputeAllDependencies(str(path))
        if unresolved:raise ValueError('S0_UNRESOLVED_DEPENDENCY')
        closure=[]
        for dependency in {Path(layer.realPath) for layer in layers if layer.realPath}|set(map(Path,dependencies)):
            dependency=dependency.resolve()
            if not dependency.is_relative_to(root.resolve()):raise ValueError('S0_DEPENDENCY_MOUNT')
            record=dict(mount='room_yazhi',path=dependency.relative_to(root.resolve()).as_posix(),sha256=sha256_file(dependency),bytes=dependency.stat().st_size)
            key=(record['mount'],record['path'])
            if key in assets and assets[key]['sha256']!=record['sha256']:raise ValueError('S0_LOCK_CONFLICT')
            assets[key]=record;closure.append(record)
        state=dict(state_id=state_id,version='1.0',usd_locator_or_native_prim=location,sha256=source['sha256'],units=1.,up_axis='Z',
            root_prim=str(prim.GetPath()),pivot=[0.,0.,0.],alignment=rows(Gf.Matrix4d(1)),state_transform=rows(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)),
            visual_bounds=visual,footprint=[[visual[0][0],visual[0][1]],[visual[1][0],visual[0][1]],[visual[1][0],visual[1][1]],[visual[0][0],visual[1][1]]],
            support_envelope=dict(clearance_m=.001),allowed_pose_tags=['flat'],acceptance_refs=[],
            physics_proxy=dict(kind='none',capability='STATIC_ONLY',shape_paths=[],geometry_hash=geometry_signature(prim)))
        states.append(state);proofs.append(dict(state_id=state_id,adoption=item['decision'],decision_locator=decision.relative_to(CODE.parent).as_posix(),
            decision_sha256=sha256_file(decision),asset_sha256=source['sha256'],geometry_hash=geometry_signature(prim),bounds=visual,closure=closure,
            scope='source selection and measured geometry only; no cross-room, support-query, visual or physics qualification'))
    entry=dict(asset_id='s0_towel',version='1.0',category='towel',origin='external',source_locator=states[0]['usd_locator_or_native_prim'],
        dependency_hashes=[r for p in proofs for r in p['closure']],root_prim=states[0]['root_prim'],
        dimensions=[max(s['visual_bounds'][1][j]-s['visual_bounds'][0][j] for s in states) for j in range(3)],
        provenance=dict(kind='ADOPTED_STATIC_MESH_STATES',decision_sha256=sha256_file(decision),human_dimensions_confirmed=False),
        license_scope='INTERNAL_EVALUATION_ONLY; REDISTRIBUTION_NOT_CLEARED',states=states,qualification_refs=[])
    catalog['entries'].append(entry);validate_contract(catalog,'Catalog');lock['assets']=list(assets.values())
    record=dict(mount='room_yazhi',path=decision.relative_to(root).as_posix(),sha256=sha256_file(decision),bytes=decision.stat().st_size,
                functions=['adoption decision metadata only'],reuse='read-only adoption provenance')
    lock['helpers'].append(record)
    write_json_new(out/'selection.json',dict(execution='EXECUTED',outcome='PASS',category='towel',states=proofs,
        distinct_geometry=proofs[0]['geometry_hash']!=proofs[1]['geometry_hash'],new_asset_generation=False,physics='STATIC_ONLY',next='WU-12 cross-room integration and eight-case acceptance'))
    (CODE/'config/catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8');(CODE/'config/source_lock.json').write_text(json.dumps(lock,indent=2),encoding='utf-8')
    print(json.dumps(dict(selected='s0_towel',states=[s['state_id'] for s in states],distinct_geometry=proofs[0]['geometry_hash']!=proofs[1]['geometry_hash'])))
