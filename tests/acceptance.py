"""Candidate-only real static acceptance. No original source/builders imported."""
import os,sys,json,subprocess,time,hashlib,ctypes,csv,re,shutil,argparse,ast
from pathlib import Path
from datetime import datetime,timezone
sys.dont_write_bytecode=True
CODE=Path(__file__).resolve().parents[1];RC=CODE.parent;DATA=RC/'asset-package';OUTPUT=RC/'local-test-outputs'
p=argparse.ArgumentParser();p.add_argument('--isaac-root',default=os.environ.get('YAZHI_ISAAC_ROOT','C:/isaac_sim'));opts=p.parse_args()
SDK=Path(opts.isaac_root).resolve();PY=SDK/'kit/python/python.exe'
sys.path.insert(0,str(CODE/'toolkit'));import runtime_support as rt
CONTRACT=rt.read(CODE/'docs/acceptance_commands.json');TAG='acceptance_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
QA=RC/'qa'/TAG;QA.mkdir();OUTPUT.mkdir(exist_ok=True);FIX=OUTPUT/(TAG+'_fixtures');FIX.mkdir()
paths={k:OUTPUT/(TAG+'_'+k) for k in ('checkout49','checkout50','stayover49','repeat49','replay49')}
vars={'SDK':str(SDK),'ASSET':str(DATA),'OUT49':str(paths['checkout49']),'OUT50':str(paths['checkout50']),'STAYOVER':str(paths['stayover49']),'REPEAT49':str(paths['repeat49']),'REPLAY49':str(paths['replay49']),'MANIFEST49':str(paths['checkout49']/'scene_manifest.json')}
CASES=[];CHECKS=[]
def save(p,j):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf8',newline='\n') as f:json.dump(j,f,indent=2,ensure_ascii=True,allow_nan=False)
def hashes(root):return {p.relative_to(root).as_posix():rt.sha(p) for p in root.rglob('*') if p.is_file()}
code_before=hashes(CODE);asset_before=hashes(DATA)
def check(name,ok,detail=None):
 row={'name':name,'pass':bool(ok),'detail':detail};CHECKS.append(row);print(name,ok,flush=True)
 if not ok:raise AssertionError(name)
def args_for(name):return [a.format(**vars) for a in CONTRACT['cases'][name]]
def run(name,args,expected=0,code_root=CODE,launcher=False,optimized=False):
 cmd=[str(PY),'-I',*(['-O'] if optimized else []),'-B',str(code_root/'toolkit/randomize.py'),*map(str,args)]
 if launcher:cmd=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(code_root/'toolkit/randomize.ps1'),*map(str,args)]
 so=QA/(name+'.stdout.txt');se=QA/(name+'.stderr.txt');start=time.monotonic();reason=None;peak=0
 class MC(ctypes.Structure):_fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ('peak_ws','ws','pp','p','np','n','pf','peakpf')]
 fn=ctypes.windll.psapi.GetProcessMemoryInfo;fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
 with so.open('xb') as o,se.open('xb') as e:
  proc=subprocess.Popen(cmd,cwd='C:/Windows',stdout=o,stderr=e)
  while proc.poll() is None:
   m=MC();m.cb=ctypes.sizeof(m)
   if fn(int(proc._handle),ctypes.byref(m),m.cb):peak=max(peak,m.ws)
   if time.monotonic()-start>120 or peak>4*2**30:reason='TIMEOUT_OR_RSS';proc.kill();break
   time.sleep(.1)
  exitcode=proc.wait()
 row={'name':name,'command':cmd,'cwd':'C:/Windows','native_exit':exitcode,'expected_exit':expected,'timeout_seconds':120,'rss_limit_bytes':4*2**30,'peak_rss_bytes':peak,'resource_monitor_scope':'Direct process; PowerShell launcher child SDK not individually RSS sampled','elapsed_seconds':time.monotonic()-start,'forced_reason':reason,'pass':exitcode==expected and reason is None,'stdout':so.name,'stderr':se.name}
 CASES.append(row);save(QA/(name+'.process.json'),row);print(name,'EXIT',exitcode,'expected',expected,flush=True)
 if not row['pass']:print(se.read_text(encoding='utf8',errors='replace')[:1800],flush=True);raise AssertionError(name)
 return row
def fake_package(name,mutate=None,first_bad=False):
 root=FIX/name;(root/'assets').mkdir(parents=True)
 j=rt.read(DATA/'asset_manifest.json')
 if mutate:
  mutate(j);save(root/'asset_manifest.json',j)
 else:shutil.copyfile(DATA/'asset_manifest.json',root/'asset_manifest.json')
 if first_bad:
  r=next(iter(rt.read(CODE/'toolkit/config/asset_lock.json')['files']));target=root/'assets'/r;target.parent.mkdir(parents=True);target.write_bytes(b'CORRUPTED_TEST_FIXTURE')
 return root
try:
 for name in ['help','preflight','checkout49','checkout50','stayover49','repeat49','saved_replay']:run(name,args_for(name))
 run('process_scoped_launcher',args_for('preflight'),launcher=True)
 run('config_example_preflight',['--config',CODE/'examples/config.example.json','--seed','49','--preflight'])
 ms={k:rt.read(v/'scene_manifest.json') for k,v in paths.items()}
 a=ms['checkout49'];b=ms['repeat49'];r=ms['replay49']
 check('same_seed_semantic_plan',a['generator_manifest']==b['generator_manifest'])
 check('same_seed_config_assets',a['configuration_fingerprint']==b['configuration_fingerprint'])
 check('same_seed_composed_geometry',a['composed_signature']==b['composed_signature'])
 check('different_seed_real_samples',a['generator_manifest']['props']!=ms['checkout50']['generator_manifest']['props'] and a['generator_manifest']['furniture']!=ms['checkout50']['generator_manifest']['furniture'])
 check('saved_replay_no_sampler',r['sampling_mode']=='SAVED_MANIFEST_POSE_RESTORE_NO_RESAMPLING' and a['generator_manifest']==r['generator_manifest'] and a['composed_signature']==r['composed_signature'])
 # Independent Stage/native readback, not only JSON success strings.
 rt.bootstrap(SDK)
 from pxr import Usd,UsdGeom as U,UsdPhysics as P
 readbacks={}
 for key,m in ms.items():
  stage=Usd.Stage.Open(str(paths[key]/'scene.usda'));check(key+'_stage',stage is not None and not stage.GetCompositionErrors())
  cache=U.XformCache();errs=[]
  for name,o in m['generator_manifest']['props'].items():
   prim=stage.GetPrimAtPath('/YAZHI_TWIN/V2Clutter/'+name);matrix=cache.GetLocalToWorldTransform(prim)
   errs.append(max(abs(matrix[i][j]-o['world_matrix'][i][j]) for i in range(4) for j in range(4)))
   check(key+'_'+name+'_asset_identity',rt.sha(DATA/'assets'/o['asset_path'])==o['asset_sha256'])
   check(key+'_'+name+'_no_new_dynamic',not prim.HasAPI(P.RigidBodyAPI))
   rt.action_policy(o['task_metadata'])
  for o in m['refined_bedding']['instances']:
   matrix=cache.GetLocalToWorldTransform(stage.GetPrimAtPath(o['path']))
   errs.append(max(abs(matrix[i][j]-o['world_matrix'][i][j]) for i in range(4) for j in range(4)))
  check(key+'_pose_threshold',max(errs)<=CONTRACT['comparison_thresholds']['pose_matrix_max_abs'],max(errs))
  dep=rt.closure(paths[key]/'scene.usda',[DATA/'assets',paths[key]])
  check(key+'_dependency_closure',not dep['unresolved'] and dep['files']==rt.read(paths[key]/'dependency_manifest.json')['files'])
  val=rt.read(paths[key]/'validation.json');rep=rt.read(paths[key]/'run_report.json')
  check(key+'_materials_and_source_joints',val['visible_material_bindings_checked']>0 and val['legacy_joints_unchanged'] and val['new_dynamic_bodies']==0)
  check(key+'_honest_scope',rep['PHYSICS']=='NOT_RUN' and rep['GUI_ACCEPTANCE']=='NOT_RUN' and rep['DISTRIBUTION_READINESS']=='BLOCKED' and m['qualification']['dynamic_instances']==[])
  check(key+'_candidate_only_imports',rep['cwd']=='C:\\Windows' and all(Path(x).is_relative_to(CODE/'toolkit') for x in rep['helper_imports'].values()))
  check(key+'_code_asset_versions',m['toolkit_version']==CONTRACT['version']==m['asset_package_version'])
  readbacks[key]={'pose_error_max':max(errs),'dependency_files':dep['file_count'],'material_bindings':val['visible_material_bindings_checked'],'signature':m['composed_signature']}
 check('checkout_guest_boundary','book' not in a['generator_manifest']['props'] and all(x['task_metadata']['ownership']!='GUEST' for x in a['generator_manifest']['props'].values()))
 guests=[x['task_metadata'] for x in ms['stayover49']['generator_manifest']['props'].values() if x['task_metadata']['ownership']=='GUEST']
 check('stayover_guest_protected',len(guests)>=2 and all(x['robot_action_policy']=='DO_NOT_TOUCH' for x in guests))
 check('modes_different',set(a['generator_manifest']['props'])!=set(ms['stayover49']['generator_manifest']['props']) and a['generator_manifest']['soft']!=ms['stayover49']['generator_manifest']['soft'])
 h=hashes(paths['checkout49']);run('existing_output_refused',['--seed','49','--output-dir',paths['checkout49']],12);check('existing_output_unchanged',h==hashes(paths['checkout49']))
 for name,path in [('asset_source',DATA/'assets'),('code_source',CODE),('outside_output',RC/'qa/not-output'),('missing_parent',OUTPUT/'parent-does-not-exist/leaf')]:run(name+'_output_refused',['--seed','49','--output',path],12)
 run('invalid_seed',['--seed','not-an-int','--preflight'],2)
 run('out_of_range_seed',['--seed',str(2**31),'--preflight'],2)
 run('invalid_task',['--seed','49','--task-mode','unknown','--preflight'],2)
 run('wrong_environment',['--seed','49','--preflight','--isaac-root',FIX/'missing-sdk'],10)
 run('missing_asset_package',['--seed','49','--preflight','--asset-package',FIX/'missing-package'],11)
 bad=fake_package('wrong-asset-version',lambda x:x.update(asset_package_version='not-compatible'))
 run('asset_version_mismatch',['--seed','49','--preflight','--asset-package',bad],13)
 bad2=fake_package('wrong-code-scope',lambda x:x.update(compatible_code_versions=[]))
 run('code_asset_compatibility_mismatch',['--seed','49','--preflight','--asset-package',bad2],13)
 bad3=fake_package('missing-file')
 run('missing_locked_data',['--seed','49','--preflight','--asset-package',bad3],11)
 bad4=fake_package('tampered-data',first_bad=True)
 run('tampered_asset_sha',['--seed','49','--preflight','--asset-package',bad4],11)
 cfg=FIX/'invalid_config.json';save(cfg,{'physics':'qualified'})
 run('invalid_config_key',['--seed','49','--preflight','--config',cfg],2)
 run('disabled_physics',['--seed','49','--physics','qualified'],21)
 run('optimized_python_refused',['--seed','49','--preflight'],10,optimized=True)
 fake=json.loads(json.dumps(a));fake['generator_manifest']['soft']['BED_LEFT']['state']='HybridSideDrape_r2';fake['generator_manifest_sha256']=rt.hash_json(fake['generator_manifest']);f=FIX/'blocked_state.json';save(f,fake)
 run('blocked_bedding_replay',['--replay',f,'--output-dir',OUTPUT/(TAG+'_blocked')],20)
 fake2=json.loads(json.dumps(a));fake2['generator_manifest']['props']['can']['asset_path']='../../outside.usda';fake2['generator_manifest_sha256']=rt.hash_json(fake2['generator_manifest']);f2=FIX/'unknown_reference.json';save(f2,fake2)
 run('unknown_asset_reference_refused',['--replay',f2,'--output',OUTPUT/(TAG+'_unknown')],11)
 for name,row in [('guest',{'ownership':'GUEST','action_candidate':'COLLECT_TRASH','robot_action_policy':'DO_NOT_TOUCH'}),('unknown',{'ownership':'UNKNOWN','action_candidate':'COLLECT_TRASH','robot_action_policy':'NEEDS_HUMAN_CONFIRMATION'}),('leftbehind',{'ownership':'HOTEL_ASSUMED_RESEARCH','task_role':'LEFT_BEHIND_CANDIDATE','action_candidate':'COLLECT_TRASH','robot_action_policy':'NEEDS_HUMAN_CONFIRMATION'}),('ambiguous_waste',{'ownership':'SYNTHETIC','category':'DECLARED_TRASH','state_evidence':'LOOKS_MESSY','action_candidate':'COLLECT_TRASH'})]:
  refused=False
  try:rt.action_policy(row)
  except rt.ToolkitError as e:refused=e.code==20
  check(name+'_action_negative',refused)
 # Independent relocated candidate, code + approved asset package only, fresh outputs.
 clone=RC.parent/('R space '+TAG[-14:])
 for source_root,relative in [(CODE,'code-repo'),(DATA,'asset-package')]:
  for src in source_root.rglob('*'):
   if src.is_file():
    dst=clone/relative/src.relative_to(source_root);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 (clone/'local-test-outputs/input').mkdir(parents=True)
 save(clone/'local-test-outputs/input/scene_manifest.json',a)
 run('relocated_preflight',['--seed','49','--preflight'],code_root=clone/'code-repo')
 run('relocated_saved_replay',['--replay',clone/'local-test-outputs/input/scene_manifest.json','--output-dir',clone/'local-test-outputs/replay'],code_root=clone/'code-repo')
 mclone=rt.read(clone/'local-test-outputs/replay/scene_manifest.json')
 check('relocated_semantic_equal',mclone['composed_signature']==a['composed_signature'])
 rc_report=rt.read(clone/'local-test-outputs/replay/run_report.json')
 check('relocated_import_paths',all(Path(x).is_relative_to(clone/'code-repo/toolkit') for x in rc_report['helper_imports'].values()))
 dep=rt.read(clone/'local-test-outputs/replay/dependency_manifest.json')
 check('relocated_all_dependencies_local',all((clone/x).is_file() and rt.sha(clone/x)==h for x,h in dep['files'].items()))
 # Every asset root, including unused rigid assets, must have a complete authored closure.
 unions={}
 for rel in rt.read(CODE/'toolkit/config/asset_lock.json')['files']:
  if Path(rel).suffix.lower() in ('.usd','.usda','.usdc'):unions.update(rt.closure(DATA/'assets'/rel,[DATA/'assets'])['files'])
 check('asset_all_usd_roots_closed',len(unions)==39,len(unions))
 # Static path/allowlist/secret checks: no credentials read outside candidate.
 forbidden=[];sensitive=[];python=[]
 secret_patterns=[('private_key',re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),('github_token',re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}')),('aws_access_id',re.compile(rb'AKIA[0-9A-Z]{16}'))]
 for base in (CODE,DATA):
  for file in base.rglob('*'):
   if not file.is_file():continue
   rel=file.relative_to(base).as_posix();parts=rel.lower().split('/')
   if any(x in parts for x in ('.git','node_modules','__pycache__','chrome-profile','cache','logs','.aws','.ssh')) or file.name.startswith('.env') or file.suffix.lower() in ('.pem','.key','.pfx','.log','.blend'):forbidden.append(str(file))
   if file.suffix.lower() in ('.py','.ps1','.json','.md','.usd','.usda','.csv') or file.name in ('.gitignore','.gitattributes','VERSION'):
    data=file.read_bytes()
    if file.suffix=='.py':ast.parse(data.decode('utf8'));python.append(rel)
    for label,pattern in secret_patterns:
     if pattern.search(data):sensitive.append({'path':str(file),'type':label}) # Never print match.
    if base==CODE and b'\r\n' in data:forbidden.append('Non-LF code text:'+rel)
 check('allowlist_no_forbidden_artifacts',not forbidden,forbidden)
 check('candidate_secret_patterns_clear',not sensitive,{'files_flagged':len(sensitive),'limits':'Allowlist + high-confidence patterns only; not formal proof of no secret'})
 code_usds=list(CODE.rglob('*.usd'))+list(CODE.rglob('*.usda'))
 check('code_asset_separation',not code_usds and not list(CODE.rglob('*.png')))
 check('code_ast_parsed',len(python)>=10,len(python))
 helptext=(QA/'help.stdout.txt').read_text(encoding='utf8')
 check('readme_flags_exist',all(x in helptext for x in ['--output-dir','--output','--asset-package','--isaac-root','--task-mode','--replay','--preflight']))
 check('readme_contract_cases_executed',all(x in {c['name'] for c in CASES} for x in CONTRACT['cases']))
 check('base_code_unchanged',code_before==hashes(CODE))
 check('base_assets_unchanged',asset_before==hashes(DATA))
 save(QA/'results.json',{'status':'PASS','code_version':CONTRACT['version'],'cases':CASES,'checks':CHECKS,'readback':readbacks,'outputs':{k:str(v) for k,v in paths.items()},'relocated_candidate':str(clone),'source_policy':'Candidate code/asset only; installed Kit Python allowed; no original research/staging/builder imports','thresholds':CONTRACT['comparison_thresholds'],'package_secret_scan':'No high-confidence matches; filenames/allowlist checked; no credential-store scan','physics':'NOT_RUN','render':'NOT_RUN','distribution':'BLOCKED'})
 print('CANDIDATE_ACCEPTANCE_PASS',QA,flush=True)
except Exception as e:
 save(QA/'results.json',{'status':'FAIL','cases':CASES,'checks':CHECKS,'reason':str(e),'remaining':'Preserve this attempt, analyze cause, repair isolated candidate only and rerun bounded related cases','physics':'NOT_RUN','distribution':'BLOCKED'})
 print('CANDIDATE_ACCEPTANCE_FAIL',QA,str(e),flush=True);raise
