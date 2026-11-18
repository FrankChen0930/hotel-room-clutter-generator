import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from density_policy import count_for
class Counts(unittest.TestCase):
    def test_inclusive_ranges(self):
        for seed in range(100):
            for level,lo,hi in [('low',10,20),('medium',30,50),('high',70,80)]:
                self.assertTrue(lo<=count_for(seed,level)<=hi)
    def test_reproducible(self):
        self.assertEqual(count_for(706,'low'),count_for(706,'low'))
