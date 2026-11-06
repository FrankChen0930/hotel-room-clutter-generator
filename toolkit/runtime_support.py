"""Static-only runtime support; no SimulationApp, renderer or network."""
import os,sys,json,re,hashlib,math
from pathlib import Path
VERSION='0.1.0-rc.1-internal'
RIGHTS=['INTERNAL_EVALUATION_ONLY','REDISTRIBUTION_NOT_CLEARED']
PKG=Path(__file__).resolve().parents[1]
TOOLKIT=PKG/'toolkit'
DEPLOY=PKG.parent
OUTPUT_ROOT=DEPLOY/'local-test-outputs'
class ToolkitError(RuntimeError):
 def __init__(self,code,message):self.code=code;super().__init__(message)
def hash_json(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,j):
 with Path(p).open('x',encoding='utf8') as f:json.dump(j,f,indent=2,ensure_ascii=False,allow_nan=False)
def reject_reparse(path):
 p=Path(path).absolute()
 for item in [p,*p.parents]:
  if item.exists() and (item.is_symlink() or getattr(item.lstat(),'st_file_attributes',0)&0x400):raise ToolkitError(12,'Symlink/junction/reparse path refused: '+str(item))
 return p.resolve()
def contained(path,root,code=12):
 p=reject_reparse(path);root=reject_reparse(root)
 if not p.is_relative_to(root):raise ToolkitError(code,'Path outside allowed root: '+str(p))
 return p
def local_path(value,base=None):
 raw=os.fspath(value)
 if not raw or re.match(r'^[a-z]+://|^[/\\\\]{2}',raw,re.I):raise ToolkitError(2,'Only explicit local filesystem paths are supported')
 p=Path(raw)
 if base is not None and not p.is_absolute():p=base/p
 return reject_reparse(p)
def input_path(value):
 p=local_path(value)
 if not any(p.is_relative_to(r) for r in (PKG,OUTPUT_ROOT)):raise ToolkitError(12,'Config/replay input must be inside code-repo or local-test-outputs')
 return p
def configure(args):
 cfg=read(TOOLKIT/'config/default.json')
 if args.config:
  p=input_path(args.config)
  try:extra=read(p)
  except (OSError,ValueError) as e:raise ToolkitError(2,'Cannot read config: '+str(e))
  if not isinstance(extra,dict):raise ToolkitError(2,'Config must be a JSON object')
  unknown=set(extra)-{'assets_dir','isaac_root'}
  if unknown:raise ToolkitError(2,'Unsupported config keys: '+str(sorted(unknown)))
  cfg.update(extra)
 sdk=local_path(args.isaac_root or cfg.get('isaac_root') or os.environ.get('YAZHI_ISAAC_ROOT','C:/isaac_sim'))
 assets=local_path(Path(args.asset_package)/'assets') if args.asset_package else local_path(cfg.get('assets_dir','../asset-package/assets'),PKG)
 return cfg,sdk,assets
def install_guard(sdk,write_root=None,assets=None):
 allowed=[PKG.resolve(),sdk.resolve(),Path(sys.base_prefix).resolve(),OUTPUT_ROOT.resolve()]
 if assets is not None:allowed.append(assets.parent.resolve())
 import_roots=[PKG.resolve(),sdk.resolve(),Path(sys.base_prefix).resolve()]
 def valid(p,roots):return any(p.is_relative_to(x) for x in roots)
 def hook(event,args):
  if event=='import' and args[0].split('.')[0] in ('isaacsim','omni','carb','bpy'):raise ToolkitError(10,'Static mode forbids runtime import: '+args[0])
  if event in ('socket.connect','subprocess.Popen'):raise ToolkitError(10,'Static CLI forbids network/child process: '+event)
  if event=='open' and not isinstance(args[0],int):
   p=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
   write=isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
   if write and (write_root is None or not p.is_relative_to(write_root)):raise ToolkitError(12,'Write outside current output refused: '+str(p))
   if not write and not valid(p,allowed):raise ToolkitError(11,'Read outside package/SDK refused: '+str(p))
  if event in ('os.remove','os.rmdir'):raise ToolkitError(12,'CLI never deletes files')
  if event in ('os.rename','os.replace'):
   if write_root is None or any(not Path(os.fsdecode(x)).resolve().is_relative_to(write_root) for x in args[:2]):raise ToolkitError(12,'Move outside output refused')
 sys.addaudithook(hook)
 sys.path[:]=[p for p in sys.path if p and valid(Path(p).resolve(),import_roots)]
def bootstrap(sdk):
 exe=sdk/'kit/python/python.exe'
 if not exe.is_file() or Path(sys.executable).resolve()!=exe.resolve():raise ToolkitError(10,'Use the configured Isaac Kit Python: '+str(exe))
 version=sdk/'VERSION'
 if not version.is_file():raise ToolkitError(10,'Missing Isaac VERSION')
 found=version.read_text().strip()
 if not found.startswith('6.0.0-rc.59'):raise ToolkitError(10,'Isaac version not validated for this toolkit: '+found)
 libs=list((sdk/'extscache').glob('omni.usd.libs-*/pxr'))
 if len(libs)!=1:raise ToolkitError(10,'Expected one bundled USD extension')
 lib=libs[0].parent;sys.path.insert(0,str(lib))
 global DLL_HANDLES
 DLL_HANDLES=[os.add_dll_directory(str(p)) for p in (lib/'bin',sdk/'kit/kernel/plugins',sdk/'kit')]
 from pxr import Usd
 return {'isaac_version':found,'python_version':sys.version,'python_executable':str(exe),'usd_version':list(Usd.GetVersion()),'simulation_app_started':False}
def record_path(path):
 try:return path.relative_to(DEPLOY).as_posix()
 except ValueError:return path.as_posix()
def closure(root,allowed):
 from pxr import Sdf,UsdUtils
 seen=set();todo=[Path(root).resolve()];edges=[];assets=set();layers=0
 while todo:
  p=todo.pop()
  if p in seen:continue
  seen.add(p)
  if not any(p.is_relative_to(x) for x in allowed):raise ToolkitError(11,'USD dependency escapes package/output: '+str(p))
  reject_reparse(p)
  if not p.is_file():raise ToolkitError(11,'Missing USD dependency: '+str(p))
  assets.add(p)
  if p.suffix.lower() not in ('.usd','.usda','.usdc'):continue
  layer=Sdf.Layer.FindOrOpen(str(p))
  if not layer:raise ToolkitError(11,'Cannot read USD layer: '+str(p))
  layers+=1;text=layer.ExportToString();sub,refs,payload=UsdUtils.ExtractExternalReferences(str(p))
  tokens=set(re.findall(r'@([^@]+)@',text))|set(sub)|set(refs)|set(payload)
  for token in sorted(tokens):
   if not token:continue
   if re.match(r'^[a-z]+://|^[A-Za-z]:[/\\]|^[/\\]',token,re.I):raise ToolkitError(11,'Non-relative USD asset reference refused: '+token)
   target=(p.parent/token).resolve()
   edges.append({'source':record_path(p),'authored_path':token,'resolved':record_path(target)})
   todo.append(target)
 return {'files':{record_path(p):sha(p) for p in sorted(assets)},'file_count':len(assets),'layer_count':layers,'edges':edges,'unresolved':[]}
def check_assets(root):
 lock=read(TOOLKIT/'config/asset_lock.json')
 mf=root.parent/'asset_manifest.json'
 if not mf.is_file():raise ToolkitError(11,'Missing Asset Package manifest; point --asset-package at a directory containing asset_manifest.json and assets/')
 try:manifest=read(mf)
 except (OSError,ValueError) as e:raise ToolkitError(11,'Invalid Asset Package manifest: '+str(e))
 compatibility=read(TOOLKIT/'config/compatibility.json')
 if (PKG/'VERSION').read_text().strip()!=VERSION or compatibility['code_version']!=VERSION:raise ToolkitError(13,'Code version files do not match runtime version')
 if manifest.get('asset_package_version')!=lock['asset_package_version'] or manifest.get('dataset_id')!=lock['dataset_id'] or VERSION not in manifest.get('compatible_code_versions',[]):raise ToolkitError(13,'Code/Asset version or dataset mismatch')
 if manifest.get('rights')!=RIGHTS or manifest.get('license_status')!='LICENSE_PENDING_HUMAN_APPROVAL':raise ToolkitError(13,'Asset rights metadata does not match the internal candidate')
 if sha(mf)!=lock['asset_manifest_sha256']:raise ToolkitError(13,'Asset manifest identity mismatch')
 if {r:v['sha256'] for r,v in manifest['files'].items()}!=lock['files']:raise ToolkitError(13,'Asset file set/hash declaration mismatch')
 for r,h in lock['files'].items():
  p=contained(root/r,root,11)
  if not p.is_file():raise ToolkitError(11,'Missing locked asset: '+r)
  if sha(p)!=h:raise ToolkitError(11,'Asset SHA mismatch: '+r)
 return lock
def semantic_fingerprint(assets):
 files={str(p.relative_to(TOOLKIT)):sha(p) for p in sorted((TOOLKIT/'config').glob('*.json')) if p.name!='default.json'}
 files.update({str(p.relative_to(TOOLKIT)):sha(p) for p in sorted((TOOLKIT/'vendor').glob('*.py'))})
 files.update({p.name:sha(p) for p in [TOOLKIT/'runtime_support.py',TOOLKIT/'randomize.py']})
 return hashlib.sha256(json.dumps({'version':VERSION,'files':files,'asset_lock':check_assets(assets)},sort_keys=True).encode()).hexdigest(),files
def action_policy(row):
 owner=row.get('ownership');action=row.get('action_candidate','NONE');role=row.get('task_role')
 if owner in ('GUEST','UNKNOWN') or role=='LEFT_BEHIND_CANDIDATE':
  if row.get('robot_action_policy') not in ('DO_NOT_TOUCH','NEEDS_HUMAN_CONFIRMATION') or action.startswith('COLLECT'):raise ToolkitError(20,'Protected/unknown/left-behind item cannot be collected')
 if row.get('category')=='DECLARED_TRASH' and not str(row.get('state_evidence','')).startswith('EXPLICIT_SYNTHETIC_AUTHOR_DECLARATION'):raise ToolkitError(20,'Waste requires explicit synthetic ground truth')
def signature(stage):
 from pxr import UsdGeom as U,Usd
 cache=U.XformCache();out={}
 for p in Usd.PrimRange.Stage(stage,Usd.TraverseInstanceProxies()):
  if not (p.IsA(U.Gprim) or p.IsA(U.Camera)):continue
  attrs={a.GetName():str(a.Get()) for a in p.GetAttributes() if a.GetName() in ('points','faceVertexCounts','faceVertexIndices','size','radius','height','axis','visibility','purpose')}
  out[str(p.GetPath())]={'world':[[float(cache.GetLocalToWorldTransform(p)[i][j]) for j in range(4)] for i in range(4)],'geometry':attrs}
 return hashlib.sha256(json.dumps(out,sort_keys=True).encode()).hexdigest()
def validate_scene(path,source,groups,colliders,manifest,bedding,assets,output):
 from pxr import Usd,UsdGeom as U,UsdPhysics as P,UsdShade
 import iterate as gen
 import common as c
 dep=closure(path,[assets,output]);stage=Usd.Stage.Open(str(path))
 if not stage or stage.GetCompositionErrors():raise ToolkitError(40,'USD readback/composition failure')
 geo=gen.validate(path,source,groups,colliders,manifest)
 cache=U.XformCache();records={}
 for name,r in manifest['props'].items():
  target=c.PREFIX+'/V2Clutter/'+name;p=stage.GetPrimAtPath(target)
  err=max(abs(cache.GetLocalToWorldTransform(p)[i][j]-r['world_matrix'][i][j]) for i in range(4) for j in range(4))
  if err>1e-8 or sha(assets/r['asset_path'])!=r['asset_sha256']:raise ToolkitError(40,'Manifest/asset pose mismatch: '+name)
  action_policy(r['task_metadata'])
  if manifest['task_mode']=='CHECKOUT_CLEANING' and r['task_metadata']['category']=='PERSONAL_BELONGING':raise ToolkitError(20,'Default checkout cannot include personal belongings')
  records[name]={'path':target,'pose_error_max':err,'support':r['support_path'],'asset_sha256':r['asset_sha256'],'qualification':'NOT_QUALIFIED_IN_TOOLKIT','action_policy':r['task_metadata']}
 # Refined assets are reused unchanged; validate finite geometry and pillow support.
 for r in bedding['instances']:
  p=stage.GetPrimAtPath(r['path']);err=max(abs(cache.GetLocalToWorldTransform(p)[i][j]-r['world_matrix'][i][j]) for i in range(4) for j in range(4))
  if err>1e-8 or sha(assets/r['asset_path'])!=r['asset_sha256']:raise ToolkitError(40,'Bedding identity/pose mismatch')
  if 'Pillow' in r['state']:
   import generate as g
   box=c.bounds(stage,[r['path']]);support=c.bounds(stage,[r['support']])
   if box['min'][2]-support['max'][2]<0.0005 or not g.contains(g.box_shape(support),g.box_shape(box),.005):raise ToolkitError(20,'Pillow support/clearance rejected')
 materials=0;meshes=0
 for p in c.prims(stage):
  if p.IsA(U.Mesh):
   meshes+=1;points=U.Mesh(p).GetPointsAttr().Get()
   if points is not None and not all(math.isfinite(v) for point in points for v in point):raise ToolkitError(40,'Non-finite mesh')
  if not p.IsA(U.Gprim) or U.Imageable(p).ComputeVisibility()=='invisible' or U.Imageable(p).ComputePurpose()=='guide':continue
  material,_=UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()
  if not material:raise ToolkitError(40,'Visible primitive lacks material: '+str(p.GetPath()))
  shader,_,_=material.ComputeSurfaceSource()
  if not shader:raise ToolkitError(40,'Material surface shader missing')
  materials+=1
 oldbodies={str(p.GetPath()) for p in c.prims(source) if p.HasAPI(P.RigidBodyAPI)}
 newbodies={str(p.GetPath()) for p in c.prims(stage) if p.HasAPI(P.RigidBodyAPI)}
 if newbodies!=oldbodies:raise ToolkitError(40,'Static generator changed rigid body set')
 return {'status':'STATIC_GEOMETRY_SUPPORT_AND_READBACK_PASS','legacy_geometry_checks':geo,'per_object':records,'dependency_closure':dep,'visible_material_bindings_checked':materials,'mesh_count':meshes,'new_dynamic_bodies':0,'legacy_joints_unchanged':True,'physics':'NOT_RUN','gui_acceptance':'NOT_RUN','human_acceptance':'PENDING','soft_collision':'NOT_CERTIFIED','duvet_contact_scope':'Immutable adopted visual mesh; no new cloth/collision certification','composed_signature':signature(stage)}
