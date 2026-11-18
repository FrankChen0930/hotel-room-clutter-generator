import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from source_variants import candidate_variant_key

def key(name,author='Artist',width=.076,polygons=100):
    a=dict(name=name,author=author,category='electronics')
    p=dict(objects=[dict(type='MESH',hidden=False,hide_render=False,polygons=polygons,
        world_bounds_m=dict(dimensions=[width,.158,.011]))])
    return candidate_variant_key(a,p)

class VariantPrescreenTests(unittest.TestCase):
    def test_source_colorways_share_a_family(self):
        self.assertEqual(key('Generic Smartphone Sky Blue'),key('Generic Smartphone Pearl White'))
    def test_different_hardware_generations_not_collapsed(self):
        self.assertNotEqual(key('iPhone16 Pro Black'),key('iPhone17 Pro Black'))
    def test_geometry_or_author_difference_kept(self):
        self.assertNotEqual(key('Smartphone Blue'),key('Smartphone White',width=.08))
        self.assertNotEqual(key('Smartphone Blue'),key('Smartphone White',polygons=120))
        self.assertNotEqual(key('Smartphone Blue'),key('Smartphone White',author='Other'))
    def test_unknown_author_cannot_establish_variant(self):
        self.assertIsNone(key('Smartphone Blue',author='UNKNOWN'))

if __name__=='__main__':unittest.main()
