import base64
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from library import ROOT,sha
from package_room_examples import package
import usd_sdk
usd_sdk.load()
from pxr import Usd,Sdf,UsdUtils,UsdGeom


class PortablePackageTests(unittest.TestCase):
    def test_nested_dependency_closure_survives_relocation(self):
        with tempfile.TemporaryDirectory(prefix='_closure_test_',dir=ROOT/'runs') as temp:
            work=Path(temp);source=work/'source';source.mkdir()
            texture=source/'tiny.png';texture.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
            child=Usd.Stage.CreateNew(str(source/'child.usda'))
            prim=child.DefinePrim('/Asset','Xform');child.SetDefaultPrim(prim)
            prim.CreateAttribute('test:texture',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('tiny.png'));child.GetRootLayer().Save()
            main=Usd.Stage.CreateNew(str(source/'main.usda'));root=main.DefinePrim('/Room','Xform');root.GetReferences().AddReference('child.usda')
            main.SetDefaultPrim(root);UsdGeom.SetStageUpAxis(main,'Z');UsdGeom.SetStageMetersPerUnit(main,1);main.GetRootLayer().Save()
            original={p.name:sha(p) for p in source.iterdir()}
            receipt=package({'clean_room.usda':source/'main.usda'},work/'bundle')
            self.assertEqual(receipt['outcome'],'LOCAL_PORTABLE_CLOSURE_PASS')
            self.assertEqual(original,{p.name:sha(p) for p in source.iterdir()})
            shutil.copytree(work/'bundle',work/'relocated')
            stage=Usd.Stage.Open(str(work/'relocated/clean_room.usda'))
            self.assertTrue(stage.GetPrimAtPath('/Room'))
            self.assertEqual(UsdGeom.GetStageUpAxis(stage),'Z')
            self.assertEqual(UsdGeom.GetStageMetersPerUnit(stage),1)
            self.assertEqual(str(stage.GetDefaultPrim().GetPath()),'/Room')
            layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(work/'relocated/clean_room.usda'))
            self.assertFalse(unresolved)
            self.assertTrue(all(Path(l.realPath).is_relative_to(work/'relocated') for l in layers))
            self.assertTrue(all(Path(str(a)).is_relative_to(work/'relocated') for a in assets))
            self.assertEqual(receipt['redistribution'],'NOT_CLEARED_DO_NOT_UPLOAD_BINARY_BUNDLE')


if __name__=='__main__':unittest.main()
