import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_surface_scenes import eligible

class EligibilityTests(unittest.TestCase):
    def test_pillow_does_not_admit_shoes_liquids_or_large_equipment(self):
        for cat,d in [('footwear',[.1,.25,.1]),('toiletry',[.03,.04,.1]),('electronics',[.39,.27,.2])]:
            self.assertFalse(eligible(dict(category=cat,dimensions_m=d),'pillow_left',[cat]))
    def test_small_flat_electronics_reserved_for_curved_pillow(self):
        a=dict(category='electronics',dimensions_m=[.014,.138,.014])
        self.assertTrue(eligible(a,'pillow_left',['electronics']))
        self.assertFalse(eligible(a,'desk',['electronics']))
    def test_bed_rejects_unhygienic_footwear_and_open_liquids(self):
        for cat in ['footwear','toiletry','food']:
            self.assertFalse(eligible(dict(category=cat,dimensions_m=[.1,.1,.1]),'bed_main',[cat]))
    def test_chair_capacity_is_not_a_bag_category_blanket_permission(self):
        self.assertFalse(eligible(dict(category='bag',dimensions_m=[.4,.45,.5]),'chair_seat',['bag']))

if __name__=='__main__':unittest.main()
