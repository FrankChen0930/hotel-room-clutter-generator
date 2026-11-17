import math
from pathlib import Path
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from pxr import Gf, Usd, UsdGeom
from common_core.adapters import extract_support, footprint_supported


class SupportTests(unittest.TestCase):
    def stage(self):
        stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
        return stage

    def test_cube_parent_translation_yaw_and_scale(self):
        s=self.stage();p=UsdGeom.Xform.Define(s,'/Parent');p.AddTranslateOp().Set((3,4,1));p.AddRotateZOp().Set(30)
        cube=UsdGeom.Cube.Define(s,'/Parent/Top');cube.CreateSizeAttr(2);cube.AddScaleOp().Set((2,1,.1))
        support=extract_support(s,cube.GetPrim());self.assertEqual(support['status'],'SUPPORTED')
        self.assertAlmostEqual(support['z'],1.1,places=6)
        self.assertTrue(footprint_supported(support,[[2.9,3.9],[3.1,3.9],[3.1,4.1],[2.9,4.1]],.01))
        self.assertFalse(footprint_supported(support,[[30,30],[31,30],[31,31],[30,31]],0))

    def test_cylinder_full_footprint(self):
        s=self.stage();c=UsdGeom.Cylinder.Define(s,'/Top');c.CreateRadiusAttr(1);c.CreateHeightAttr(.2)
        result=extract_support(s,c.GetPrim());self.assertEqual(result['shape'],'circle')
        self.assertTrue(footprint_supported(result,[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]],.01))
        self.assertFalse(footprint_supported(result,[[-.9,-.9],[.9,-.9],[.9,.9],[-.9,.9]],0))

    def test_tilt_shear_and_ellipse_unknown(self):
        for mode in ['tilt','shear','ellipse']:
            s=self.stage();c=UsdGeom.Cylinder.Define(s,'/Top')
            if mode=='tilt':c.AddRotateXOp().Set(20)
            elif mode=='ellipse':c.AddScaleOp().Set((2,1,1))
            else:
                m=Gf.Matrix4d(1);m[0,1]=.3;c.AddTransformOp().Set(m)
            self.assertEqual(extract_support(s,c.GetPrim())['status'],'UNKNOWN')

    def test_mesh_top(self):
        s=self.stage();mesh=UsdGeom.Mesh.Define(s,'/Top');mesh.CreateSubdivisionSchemeAttr('none');mesh.CreatePointsAttr([(-1,-1,.5),(1,-1,.5),(1,1,.5),(-1,1,.5)])
        mesh.CreateFaceVertexCountsAttr([3,3]);mesh.CreateFaceVertexIndicesAttr([0,1,2,0,2,3])
        result=extract_support(s,mesh.GetPrim());self.assertEqual(result['status'],'SUPPORTED')
        self.assertTrue(footprint_supported(result,[[-.1,-.1],[.1,-.1],[.1,.1],[-.1,.1]],.01))

    def test_hole_not_covered_by_four_corners(self):
        s=self.stage();mesh=UsdGeom.Mesh.Define(s,'/Top');mesh.CreateSubdivisionSchemeAttr('none')
        mesh.CreatePointsAttr([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),(-.2,-.2,0),(.2,-.2,0),(.2,.2,0),(-.2,.2,0)])
        ids=[0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
        mesh.CreateFaceVertexCountsAttr([3]*8);mesh.CreateFaceVertexIndicesAttr(ids)
        result=extract_support(s,mesh.GetPrim());self.assertEqual(result['status'],'UNKNOWN')
        self.assertFalse(footprint_supported(result,[[-.8,-.8],[.8,-.8],[.8,.8],[-.8,.8]],0))

    def test_unknown_type_and_missing_prim(self):
        s=self.stage();x=UsdGeom.Xform.Define(s,'/Other')
        self.assertEqual(extract_support(s,x.GetPrim())['status'],'UNKNOWN')
        self.assertEqual(extract_support(s,s.GetPrimAtPath('/Missing'))['status'],'UNKNOWN')
