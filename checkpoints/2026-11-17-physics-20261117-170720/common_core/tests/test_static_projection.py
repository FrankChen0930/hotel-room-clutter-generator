from pathlib import Path
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Usd,UsdGeom
from common_core.adapters import footprint_supported
from common_core.validation import composed_footprint


class StaticProjectionTests(unittest.TestCase):
    def test_rotated_book_uses_geometry_projection_on_round_support(self):
        stage=Usd.Stage.CreateInMemory();cube=UsdGeom.Cube.Define(stage,'/Book');cube.CreateSizeAttr(.4)
        cube.AddTranslateOp().Set((.5,0,.2));cube.AddRotateZOp().Set(45)
        support=dict(status='SUPPORTED',shape='circle',center=[0.,0.],radius=.8)
        actual=composed_footprint(stage,cube.GetPrim())
        self.assertTrue(footprint_supported(support,actual,0.))
        lo=[min(p[j] for p in actual) for j in range(2)];hi=[max(p[j] for p in actual) for j in range(2)]
        aabb=[[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]]
        self.assertFalse(footprint_supported(support,aabb,0.))
