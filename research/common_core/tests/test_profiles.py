import ast
import copy
from pathlib import Path
import tempfile
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Usd,UsdGeom
from common_core.adapters import extract_support
from common_core.identity import sha256_file
from common_core.paths import RUN_ROOT
from common_core.room import Inputs,geometry_signature,prepare_room,rows
from common_core.planner import plan_requests
from common_core.placer import place_requests
from common_core.writer import write_scene,object_prim
from fixtures import catalog,matrix,policy,profile

CODE=Path(__file__).resolve().parents[1]


class ProfileGenericityTests(unittest.TestCase):
    def synthetic(self,folder,name,shift,sphere=False):
        path=folder/(name+'.usda');stage=Usd.Stage.CreateNew(str(path));root=UsdGeom.Xform.Define(stage,'/'+name)
        root.AddTranslateOp().Set((*shift,0.));prim_path='/'+name+'/Platform'
        geometry=UsdGeom.Sphere.Define(stage,prim_path) if sphere else UsdGeom.Cube.Define(stage,prim_path)
        if not sphere:geometry.CreateSizeAttr(2.)
        stage.SetDefaultPrim(root.GetPrim());UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z');stage.GetRootLayer().Save()
        p=profile();p['profile_id']=name;p['source'].update(path=path.name,root_prim='/'+name,sha256=sha256_file(path))
        p['source_objects']=[dict(object_id='platform',prim=prim_path,mobility='FIXED',allowed_operations=[])]
        support=p['supports'][0];support.update(prim=prim_path,collider=prim_path,kind='primitive_top',geometry_hash=geometry_signature(geometry.GetPrim()),tags=['flat'])
        if not sphere:support['allowed_region']=extract_support(stage,geometry.GetPrim())['polygon']
        a=catalog();a['entries'][0]['states'][0]['state_transform']=matrix()
        asset=folder/'cup.usda'
        if not asset.exists():
            s=Usd.Stage.CreateNew(str(asset));cup=UsdGeom.Cube.Define(s,'/Cup');cup.CreateSizeAttr(.1)
            s.SetDefaultPrim(cup.GetPrim());UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z');s.GetRootLayer().Save()
        a['entries'][0]['source_locator'].update(mount='room',path='cup.usda')
        a['entries'][0]['states'][0]['usd_locator_or_native_prim']=dict(mount='room',path='cup.usda')
        a['entries'][0]['states'][0]['sha256']=sha256_file(asset)
        pol=policy()
        for scenario in pol['scenarios'].values():
            scenario['allowed_support_tags']=['flat'];scenario['roles']=[dict(role='guest',category='cup',priority=0,
                semantics=dict(ownership='GUEST',action_policy='DO_NOT_TOUCH',task_role='PERSONAL_ITEM'))]
        return Inputs(p,a,pol,dict(room=str(folder)),{})

    def test_renamed_translated_room_uses_identical_core(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            folder=Path(temp);results=[]
            for name,shift in [('LaboratoryA',(0.,0.)),('DifferentRoot',(10.,-20.))]:
                inputs=self.synthetic(folder,name,shift);room=prepare_room(inputs.profile,inputs.bindings)
                plan=plan_requests(inputs,709,'STAYOVER','low');placed=place_requests(plan,room,inputs.catalog)
                self.assertEqual(placed['status'],'PASS');scene=write_scene(folder/(name+'-scene.usda'),inputs,placed)
                observed=[]
                for obj in placed['objects']:
                    actual=rows(UsdGeom.Xformable(scene.GetPrimAtPath(object_prim(obj))).ComputeLocalToWorldTransform(0))
                    actual[3][0]-=shift[0];actual[3][1]-=shift[1];observed.append(actual)
                results.append(observed)
            for a,b in zip(*results):
                self.assertLess(max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4)),1e-12)

    def test_unknown_support_is_not_pass(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            inputs=self.synthetic(Path(temp),'Unsupported',(0.,0.),sphere=True)
            with self.assertRaisesRegex(ValueError,'SUPPORT_GEOMETRY_UNKNOWN'):prepare_room(inputs.profile,inputs.bindings)

    def test_core_has_no_room_names_or_historical_main_imports(self):
        for name in ['planner.py','placer.py','writer.py']:
            source=(CODE/'common_core'/name).read_text(encoding='utf-8')
            for literal in ['YAZHI','hotel705','_7052','/root/']:self.assertNotIn(literal,source)
            for node in ast.walk(ast.parse(source)):
                if isinstance(node,ast.ImportFrom):self.assertNotIn(node.module or '',['generate','prepare','pilot','geometry_check'])
