from pathlib import Path
import tempfile
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Usd,UsdGeom,UsdPhysics
from common_core.paths import RUN_ROOT
from common_core.room import load_inputs,prepare_room
from common_core.planner import plan_requests
from common_core.placer import place_requests
from common_core.writer import write_scene

CODE=Path(__file__).resolve().parents[1]


def snapshot(stage,root):
    records={}
    for p in Usd.PrimRange(stage.GetPrimAtPath(root),Usd.TraverseInstanceProxies()):
        records[str(p.GetPath())]=dict(type=p.GetTypeName(),active=p.IsActive(),instance=p.IsInstanceable(),
            attributes={a.GetName():str(a.Get()) for a in p.GetAttributes()},
            relationships={r.GetName():list(map(str,r.GetTargets())) for r in p.GetRelationships()})
    return records


class YazhiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=load_inputs(CODE/'config/deployment.local.json','yazhi');cls.cache=prepare_room(cls.inputs.profile,cls.inputs.bindings)

    def test_analytic_supports_and_no_native_cross_room_leak(self):
        self.assertEqual(set(self.cache.supports),{'round_table','cabinet','bench'})
        self.assertEqual(self.cache.native_initial,{})
        for scenario in ['STAYOVER','CHECKOUT']:
            plan=plan_requests(self.inputs,706,scenario,'high')
            self.assertTrue(all(r['origin']=='external' for r in plan['requests']))
            result=place_requests(plan,self.cache,self.inputs.catalog)
            self.assertEqual(result['status'],'PASS')

    def test_source_hierarchy_joint_attributes_and_relationships_preserved(self):
        plan=plan_requests(self.inputs,706,'CHECKOUT','medium');result=place_requests(plan,self.cache,self.inputs.catalog)
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            scene=write_scene(Path(temp)/'scene.usda',self.inputs,result)
            source=Usd.Stage.Open(str(self.cache.source_path))
            original=snapshot(source,self.inputs.profile['source']['root_prim'])
            current=snapshot(scene,self.inputs.profile['source']['root_prim'])
            self.assertEqual(original,current)
            self.assertEqual([str(p.path) for p in scene.GetRootLayer().rootPrims],['/CommonCore'])

    def test_unknown_room_and_wrong_profile_contract_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN_ROOM'):load_inputs(CODE/'config/deployment.local.json','not-a-room')
