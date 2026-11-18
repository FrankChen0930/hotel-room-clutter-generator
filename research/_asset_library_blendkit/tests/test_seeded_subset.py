import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hotel_metadata import choose_local_subset

class SeededSubsetTests(unittest.TestCase):
    def test_density_independent_of_catalog_size_and_replay(self):
        pool=[dict(asset_id=f'{category}-{i}',category=category) for category in ('bag','luggage','clothing','footwear','paper','towel') for i in range(10)]
        before=[dict(a) for a in pool]
        chosen=choose_local_subset(pool,706)
        self.assertEqual(len(chosen),5)
        self.assertEqual(chosen,choose_local_subset(list(reversed(pool)),706))
        self.assertEqual(pool,before)
        self.assertEqual(len({x['asset_id'] for x in chosen}),5)
        for category in ('bag','luggage','clothing','footwear'):self.assertEqual(sum(x['category']==category for x in chosen),1)
        self.assertNotEqual(chosen,choose_local_subset(pool,707))

    def test_small_pool_not_repeated_to_fill_quota(self):
        pool=[dict(asset_id='one',category='bag')]
        self.assertEqual(choose_local_subset(pool,706),pool)
        with self.assertRaises(ValueError):choose_local_subset(pool,706,0)

if __name__=='__main__':unittest.main()
