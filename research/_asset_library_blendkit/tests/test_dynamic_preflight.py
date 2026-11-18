import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import usd_sdk
usd_sdk.load()
from pxr import Usd,UsdGeom,UsdPhysics
from dynamic_preflight import prepare_generated,disable_empty_colliders

class PreflightTests(unittest.TestCase):
    def test_empty_mesh_collider_disabled_without_changing_valid_geometry(self):
        s=Usd.Stage.CreateInMemory();empty=UsdGeom.Mesh.Define(s,'/Room/Empty');UsdPhysics.CollisionAPI.Apply(empty.GetPrim())
        valid=UsdGeom.Mesh.Define(s,'/Room/Valid');valid.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0)]);UsdPhysics.CollisionAPI.Apply(valid.GetPrim())
        self.assertEqual(['/Room/Empty'],disable_empty_colliders(s));self.assertTrue(UsdPhysics.CollisionAPI(valid).GetCollisionEnabledAttr().Get())
    def test_envelope_excludes_body_world_translation(self):
        s=Usd.Stage.CreateInMemory();root=UsdGeom.Xform.Define(s,'/CommonCore/Thing');root.AddTranslateOp().Set((3,-5,.7));UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
        UsdGeom.Cube.Define(s,'/CommonCore/Thing/Visual').CreateSizeAttr(.1)
        result=prepare_generated(s,{'/CommonCore/Thing':{}},native_tuning=False)
        p=s.GetPrimAtPath('/CommonCore/Thing/ExperimentalRigidEnvelope');box=UsdGeom.BBoxCache(0,['default']).ComputeWorldBound(p).ComputeAlignedRange()
        for a,b in zip(box.GetMin(),[2.95,-5.05,.65]):self.assertAlmostEqual(a,b,places=6)
        self.assertTrue(result['bodies'][0]['rigid_envelope_added'])
    def test_nested_body_is_removed_without_removing_parent(self):
        s=Usd.Stage.CreateInMemory();root=UsdGeom.Xform.Define(s,'/CommonCore/Thing').GetPrim();UsdPhysics.RigidBodyAPI.Apply(root)
        cube=UsdGeom.Cube.Define(s,'/CommonCore/Thing/Visual').GetPrim();UsdPhysics.RigidBodyAPI.Apply(cube).CreateRigidBodyEnabledAttr(False);UsdPhysics.CollisionAPI.Apply(cube)
        result=prepare_generated(s,{'/CommonCore/Thing':{}},native_tuning=False)
        self.assertFalse(cube.HasAPI(UsdPhysics.RigidBodyAPI));self.assertTrue(root.HasAPI(UsdPhysics.RigidBodyAPI));self.assertEqual(1,len(result['bodies'][0]['nested_body_apis_removed']))

if __name__=='__main__':unittest.main()
