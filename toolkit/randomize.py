"""YAZHI-TWIN internal static randomizer. Requires installed Isaac Kit Python."""
import sys,os,json,argparse,random,time,traceback
from pathlib import Path
from datetime import datetime,timezone
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import runtime_support as rt
def parser():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--seed',type=int)
 p.add_argument('--task-mode',choices=['checkout','stayover'],default=None)
 p.add_argument('--output','--output-dir',dest='output',help='New directory below deployment local-test-outputs/; not a USD filename')
 p.add_argument('--asset-package',help='Independent package root containing asset_manifest.json and assets/')
 p.add_argument('--config',help='Local package config override: assets_dir/isaac_root only')
 p.add_argument('--isaac-root',help='Installed Isaac root; no install or upgrade')
 p.add_argument('--preflight',action='store_true',help='Validate environment/assets only, no output writes')
 p.add_argument('--physics',choices=['none','qualified'],default='none',help='Only none is supported; qualified is refused')
 p.add_argument('--replay',help='Saved scene_manifest.json; restore saved poses without sampling')
 return p
def main(argv=None):
 args=parser().parse_args(argv);out=None;claimed=False;start=time.monotonic();phase='arguments'
 try:
  if not __debug__:raise rt.ToolkitError(10,'Optimized Python is not supported; existing geometry checks require assertions')
  if args.physics!='none':raise rt.ToolkitError(21,'P4 is not authorized. Physics interface is disabled; no old qualification is activated.')
  if args.seed is None and not args.replay:raise rt.ToolkitError(2,'--seed is required unless --replay is supplied')
  if args.seed is not None and not -(2**31)<=args.seed<2**31:raise rt.ToolkitError(2,'Seed must be a signed32-bit integer')
  cfg,sdk,assets=rt.configure(args)
  if not args.preflight:
   target=rt.local_path(args.output) if args.output else rt.OUTPUT_ROOT/('run_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
   out=rt.contained(target,rt.OUTPUT_ROOT)
   if out==rt.OUTPUT_ROOT or out.exists():raise rt.ToolkitError(12,'Output must be a NEW directory below deployment local-test-outputs/')
   if not out.parent.is_dir():raise rt.ToolkitError(12,'Output parent must already exist below local-test-outputs/')
  rt.install_guard(sdk,out,assets)
  phase='environment';env=rt.bootstrap(sdk)
  phase='assets';lock=rt.check_assets(assets);dep=rt.closure(assets/'room/usd/YAZHI_TWIN.usd',[assets])
  fingerprint,code_files=rt.semantic_fingerprint(assets)
  if args.preflight:
   print(json.dumps({'status':'PREFLIGHT_PASS','environment':env,'code_version':rt.VERSION,'asset_package_version':lock['asset_package_version'],'asset_files_checked':len(lock['files']),'canonical_dependency_files':dep['file_count'],'rights':rt.RIGHTS,'physics':'NOT_RUN','mode':'STATIC_GENERATION_ONLY','output_written':False},ensure_ascii=False));return 0
  phase='setup'
  sys.path.insert(0,str(rt.TOOLKIT/'vendor'))
  import common as c
  c.ROOT=assets;c.ROOM=assets/'room/usd/YAZHI_TWIN.usd'
  import generate as g
  import iterate as gen
  import task_helpers as task
  # Bind before sampling; no import from original project or Physics modules.
  for module in (g,gen,task):module.ROOT=assets;module.ROOM=c.ROOM
  task.a.ROOT=assets
  source=c.Usd.Stage.Open(str(c.ROOM));groups,colliders=g.discover(source)
  if args.replay:
   path=rt.input_path(args.replay);saved=rt.read(path)
   if saved.get('generator_manifest_sha256')!=rt.hash_json(saved['generator_manifest']):raise rt.ToolkitError(11,'Saved generator manifest integrity mismatch')
   if saved['configuration_fingerprint']!=fingerprint:raise rt.ToolkitError(11,'Replay config/code/assets fingerprint mismatch')
   m=saved['generator_manifest'];seed=m['seed'];mode=m['task_mode']
   if args.seed is not None and args.seed!=seed:raise rt.ToolkitError(2,'Replay seed conflicts with manifest')
   if args.task_mode and ('CHECKOUT_CLEANING' if args.task_mode=='checkout' else 'STAYOVER_CLEANING')!=mode:raise rt.ToolkitError(2,'Replay task conflicts with manifest')
   replay_kind='SAVED_MANIFEST_POSE_RESTORE_NO_RESAMPLING'
  else:
   seed=args.seed;mode='STAYOVER_CLEANING' if args.task_mode=='stayover' else 'CHECKOUT_CLEANING'
   states=rt.read(rt.TOOLKIT/'config/asset_states.json');asset_paths={k:assets/v['path'] for k,v in states['rigid'].items()}
   furniture=gen.furniture(source,groups,colliders,random.Random(seed),'SeatingTableUse')
   m=task.task_plan(seed,mode,source,groups,colliders,asset_paths,furniture)
   replay_kind='DETERMINISTIC_SEEDED_SAMPLING'
  # Enforce selected verified functional subset even for supplied replay.
  allowed={'NeatCanonical','SideDrape'}
  if any(r['state'] not in allowed for r in m['soft'].values()):raise rt.ToolkitError(20,'Blocked/unaccepted duvet state in plan')
  mobility=rt.read(rt.TOOLKIT/'config/furniture_mobility.json')
  for name,r in m['furniture'].items():
   if not mobility['items'][name]['generator_randomization_allowed'] and c.mat(r['delta'])!=c.Gf.Matrix4d(1):raise rt.ToolkitError(20,'Furniture policy violation: '+name)
  # Validate replay asset identity before any native USD reference can be authored.
  asset_definitions=rt.read(rt.TOOLKIT/'config/asset_states.json')['rigid']
  if type(seed) is not int or not -(2**31)<=seed<2**31:raise rt.ToolkitError(2,'Invalid replay seed')
  if mode not in task.POLICY['modes']:raise rt.ToolkitError(20,'Unsupported task mode')
  if set(m['soft'])!={'BED_LEFT','BED_RIGHT'}:raise rt.ToolkitError(20,'Unexpected bedding target set')
  for key,r in m['props'].items():
   expected=asset_definitions.get(r['asset'])
   if not expected or r['asset_path']!=expected['path'] or r['asset_sha256']!=expected['sha256']:raise rt.ToolkitError(11,'Replay asset identity is not allowlisted: '+key)
   if r['task_metadata']!=task.metadata(r['asset'],mode):raise rt.ToolkitError(20,'Replay ownership/action metadata differs from task policy')
  phase='output_claim';out.mkdir();claimed=True
  def receipt(n,status,detail):rt.dump(out/f'{n:02d}_{status}.json',{'phase':status,'detail':detail,'utc':datetime.now(timezone.utc).isoformat()})
  receipt(1,'PREPARED',{'seed':seed,'task':mode,'configuration_fingerprint':fingerprint})
  generated=out/'generated'/mode;refined=out/'refined'/mode
  generated.mkdir(parents=True);refined.mkdir(parents=True)
  phase='derive'
  base=generated/f'seed_{seed}_preview.usda'
  gen.derive(base,groups,m) # extracted rigid-only derive; never remodel bedding
  rt.dump(generated/f'seed_{seed}_manifest.json',m)
  gen.validate(base,source,groups,colliders,m)
  states=rt.read(rt.TOOLKIT/'config/asset_states.json')['bedding']
  state_paths={k:assets/v['path'] for k,v in states.items()}
  scene=refined/f'seed_{seed}_preview.usda'
  bm=task.bedding(scene,seed,mode,state_paths,m)
  final=c.Usd.Stage.CreateNew(str(out/'scene.usda'));root=c.U.Xform.Define(final,c.PREFIX);final.SetDefaultPrim(root.GetPrim());root.GetPrim().GetReferences().AddReference(c.relative(scene,out/'scene.usda'));c.U.SetStageUpAxis(final,'Z');c.U.SetStageMetersPerUnit(final,1)
  final.GetRootLayer().customLayerData={'toolkit_version':rt.VERSION,'status':'STATIC_PREVIEW','physics':'NOT_RUN','gui_acceptance':'NOT_RUN','rights':'INTERNAL_EVALUATION_ONLY;REDISTRIBUTION_NOT_CLEARED'};final.GetRootLayer().Save()
  receipt(2,'GENERATED',{'scene':'scene.usda'})
  phase='validation';validation=rt.validate_scene(out/'scene.usda',source,groups,colliders,m,bm,assets,out)
  module_paths={k:str(Path(v.__file__).resolve()) for k,v in sys.modules.items() if k in ('common','generate','iterate','task_helpers','bedding_helpers','geometry_check','randomize_table')}
  if not all(Path(p).is_relative_to(rt.TOOLKIT) for p in module_paths.values()):raise rt.ToolkitError(40,'Unexpected helper import path')
  manifest={'toolkit_version':rt.VERSION,'asset_package_version':lock['asset_package_version'],'seed':seed,'task_mode':mode,'configuration_fingerprint':fingerprint,'code_config_files':code_files,'asset_lock':lock,'generator_manifest':m,'generator_manifest_sha256':rt.hash_json(m),'refined_bedding':bm,'sampling_mode':replay_kind,'scene':'scene.usda','scene_sha256':rt.sha(out/'scene.usda'),'composed_signature':validation['composed_signature'],'qualification':{'mode':'STATIC_ONLY','runtime':'NOT_RUN','dynamic_instances':[],'old_profiles_or_ledger_used':False,'all_rigid_instances':'NOT_QUALIFIED_IN_TOOLKIT','soft_objects':'VISUAL_ONLY'},'rights':rt.RIGHTS,'human_visual_acceptance':'PENDING','gui_acceptance':'NOT_RUN'}
  rt.dump(out/'scene_manifest.json',manifest);rt.dump(out/'validation.json',validation)
  rt.dump(out/'dependency_manifest.json',validation['dependency_closure'])
  report={'status':'STATIC_GENERATION_PASS','IMPLEMENTATION_VALIDITY':'PASS_FOR_THIS_EXECUTION','STATIC_GENERATION_VALIDITY':'PASS','PHYSICS':'NOT_RUN','GUI_ACCEPTANCE':'NOT_RUN','HUMAN_ACCEPTANCE':'PENDING','COLLISION_CERTIFICATION':'NOT_CERTIFIED','DISTRIBUTION_READINESS':'BLOCKED','rights':rt.RIGHTS,'seed':seed,'task_mode':mode,'scene':'scene.usda','manifest':'scene_manifest.json','elapsed_seconds':time.monotonic()-start,'cwd':str(Path.cwd()),'package_root':str(rt.PKG),'helper_imports':module_paths,'guard':'Reads restricted to package/SDK; Python writes restricted to claimed output; no network/runtime imports/subprocess allowed','environment':env,'asset_package_version':lock['asset_package_version'],'asset_root':str(assets),'replay_kind':replay_kind,'blocked_states':task.POLICY['subset_limitations'],'new_asset_modeling':False}
  rt.dump(out/'run_report.json',report);receipt(3,'COMPLETE',{'status':report['status']})
  print(json.dumps({'status':report['status'],'output':str(out),'seed':seed,'task_mode':mode,'physics':'NOT_RUN','rights':rt.RIGHTS},ensure_ascii=False));return 0
 except Exception as e:
  code=e.code if isinstance(e,rt.ToolkitError) else 40
  error={'status':'FAILED','exit_code':code,'phase':phase,'error_type':type(e).__name__,'reason':str(e),'physics':'NOT_RUN','rights':rt.RIGHTS}
  if claimed and out and out.is_dir() and not (out/'run_report.json').exists():
   # Only an output claimed by this invocation may receive failure evidence.
   if (out/'01_PREPARED.json').exists():
    try:rt.dump(out/'failure.json',{**error,'traceback':traceback.format_exc()})
    except Exception:pass
  print(json.dumps(error,ensure_ascii=False),file=sys.stderr);return code
if __name__=='__main__':raise SystemExit(main())
