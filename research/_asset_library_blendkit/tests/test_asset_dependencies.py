from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from asset_dependencies import linked_asset_datablocks

class AssetDependencyTests(unittest.TestCase):
    def test_unrelated_libraries_do_not_block_local_asset(self):
        obj=N(name='actual',library=None,data=N(name='mesh',library=None),material_slots=[],instance_collection=None)
        unrelated_library=N(name='unrelated',library=object())
        self.assertEqual(linked_asset_datablocks([obj]),[])
    def test_linked_mesh_is_detected(self):
        obj=N(name='actual',library=None,data=N(name='linked_mesh',library=object()),material_slots=[],instance_collection=None)
        self.assertEqual(linked_asset_datablocks([obj]),['linked_mesh'])
    def test_linked_texture_is_detected(self):
        image=N(name='linked_image',library=object())
        tree=N(name='tree',library=None,nodes=[N(image=image,node_tree=None)])
        mat=N(name='mat',library=None,node_tree=tree)
        obj=N(name='actual',library=None,data=None,material_slots=[N(material=mat)],instance_collection=None)
        self.assertEqual(linked_asset_datablocks([obj]),['linked_image'])
