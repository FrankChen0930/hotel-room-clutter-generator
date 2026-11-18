"""New hotel prop queries must retain existing relevance and permission exclusions."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from batch_selection import choose

def item(name,**kw):
    return dict(name=name,assetBaseId=name,license='cc_zero',isFree=True,canDownload=True,assetType='model',**kw)

class RigidSearchTests(unittest.TestCase):
    def test_new_guest_prop_types(self):
        for name,category in [('Wireless mouse','electronics'),('Travel mug','food'),('Sunglasses','personal'),('Perfume bottle','toiletry')]:
            self.assertEqual(choose([item(name)],category)[0],0)

    def test_display_and_irrelevant_items_still_excluded(self):
        for name,category in [('Sunglasses display stand','personal'),('Camera studio','electronics'),('Rifle scope camera','electronics'),('Sports car','food')]:
            self.assertIsNone(choose([item(name)],category)[0])

    def test_guest_props_exclude_building_equipment(self):
        for name,category in [('Security camera','electronics'),('CCTV camera','electronics'),('Piano keys','personal'),('Watch tower','personal')]:
            self.assertIsNone(choose([item(name)],category)[0])

    def test_razor_clam_is_not_a_grooming_razor(self):
        self.assertIsNone(choose([item('Seashell Razor Clam - more skin')],'toiletry')[0])
        self.assertEqual(choose([item('Safety Razor')],'toiletry')[0],0)

    def test_modern_device_names_do_not_require_a_separate_phone_word(self):
        for name in ('iPhone15Pro','Apple iPadPro','Smartphone','AirPods3','MacBookAir','Logitech Mouse'):
            self.assertEqual(choose([item(name)],'electronics')[0],0,name)
        self.assertIsNone(choose([item('iPadPro display stand')],'electronics')[0])

if __name__=='__main__': unittest.main()
