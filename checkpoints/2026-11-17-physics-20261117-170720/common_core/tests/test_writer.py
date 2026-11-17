import copy
import json
from pathlib import Path
import tempfile
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Gf,Usd,UsdGeom
from common_core.contracts import load_json
from common_core.identity import sha256_file
from common_core.paths import RUN_ROOT,guard_new_output
from common_core.room import Inputs,rows
from common_core.writer import write_scene,set_world
from fixtures import matrix,profile


class WriterTests(unittest.TestCase):
    def fixture(self,root):
        source=root/'source.usda';stage=Usd.Stage.CreateNew(str(source));p=UsdGeom.Xform.Define(stage,'/Room')
        p.AddTranslateOp().Set((5,2,1));UsdGeom.Cube.Define(stage,'/Room/Cup').CreateSizeAttr(.1)
        stage.SetDefaultPrim(p.GetPrim());UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z');stage.GetRootLayer().Save()
        p=profile();p['source']['path']='source.usda';p['source']['sha256']=sha256_file(source)
        attributes=['xformOpOrder','xformOp:transform:commoncore','physics:kinematicEnabled','physics:rigidBodyEnabled','commoncore:semantics']
        p['override_allowlist']=[dict(prim='/Room/Cup',attributes=attributes)]
        p['source_objects'].append(dict(object_id='cup',prim='/Room/Cup',mobility='MOVABLE',allowed_operations=attributes))
        inputs=Inputs(p,dict(entries=[dict(asset_id='cup')]),None,dict(room=str(root)),{})
        pose=matrix();pose[3]=[.3,.5,.8,1.]
        obj=dict(instance_id='guest/cup/0',asset_id='cup',origin='native',native_prim='/Room/Cup',
                 effective=dict(world_matrix=pose,semantic_state=dict(ownership='GUEST',action_policy='DO_NOT_TOUCH')))
        return inputs,dict(objects=[obj]),source

    def test_parent_inverse_source_unchanged_and_relative_arc(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            root=Path(temp);inputs,result,source=self.fixture(root);before=sha256_file(source)
            nested=root/'new output';nested.mkdir();scene=nested/'scene.usda';stage=write_scene(scene,inputs,result)
            actual=rows(UsdGeom.Xformable(stage.GetPrimAtPath('/Room/Cup')).ComputeLocalToWorldTransform(0))
            self.assertLess(max(abs(actual[i][j]-result['objects'][0]['effective']['world_matrix'][i][j]) for i in range(4) for j in range(4)),1e-12)
            self.assertEqual(stage.GetRootLayer().subLayerPaths,['../source.usda']);self.assertEqual(before,sha256_file(source))

    def test_unlisted_native_override_rejected_before_scene_write(self):
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            root=Path(temp);inputs,result,_=self.fixture(root);result['objects'][0]['native_prim']='/Room/Table'
            with self.assertRaisesRegex(ValueError,'SOURCE_OVERRIDE_NOT_ALLOWED'):write_scene(root/'bad.usda',inputs,result)
            self.assertFalse((root/'bad.usda').exists())

    def test_output_guard_rejects_source_existing_and_escape(self):
        with self.assertRaisesRegex(ValueError,'OUTPUT_OUTSIDE_RUN_ROOT'):guard_new_output(Path(__file__).parents[1]/'bad-output')
        with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):guard_new_output(RUN_ROOT/'work_units')
        with self.assertRaisesRegex(ValueError,'OUTPUT_OUTSIDE_RUN_ROOT'):guard_new_output(RUN_ROOT/'..'/'escape')

    def test_asset_sha_mismatch_on_input_loading(self):
        from common_core.room import load_inputs
        code=Path(__file__).resolve().parents[1];deployment=load_json(code/'config/deployment.local.json')
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            root=Path(temp);catalog=load_json(code/'config/catalog.json');catalog['entries'][0]['states'][0]['sha256']='0'*64
            (root/'catalog.json').write_text(json.dumps(catalog),encoding='utf-8')
            deployment['catalog']=str(root/'catalog.json');deployment['source_lock']=str(code/'config/source_lock.json')
            deployment['rooms']['hotel705']=str(code/'config/rooms/hotel705.json');deployment['policy']=str(code/'config/policy.json')
            policy=load_json(code/'config/policy.json');policy['release_frozen']=False
            (root/'policy.json').write_text(json.dumps(policy),encoding='utf-8');deployment['policy']=str(root/'policy.json')
            (root/'deployment.json').write_text(json.dumps(deployment),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'SOURCE_HASH_MISMATCH'):load_inputs(root/'deployment.json','hotel705')
