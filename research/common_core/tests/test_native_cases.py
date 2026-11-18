import unittest
from common_core.support_validation import classify_hits


class NativeQueryTests(unittest.TestCase):
    def test_expected_collider_height_and_exclusions(self):
        hits=[dict(collider='/Added/Shape',z=.9,distance=.0001),dict(collider='/Source/Top',z=.75,distance=.001)]
        result=classify_hits(hits,['/Added'],'/Source/Top',.75)
        self.assertTrue(result['passed']);self.assertEqual(len(result['excluded']),1)

    def test_wrong_source_missing_hit_and_wrong_height_fail(self):
        self.assertFalse(classify_hits([],[],'/Source',.75)['passed'])
        hit=dict(collider='/Other',z=.75,distance=.001)
        self.assertFalse(classify_hits([hit],[],'/Source',.75)['passed'])
        hit=dict(collider='/Source',z=.76,distance=.001)
        self.assertFalse(classify_hits([hit],[],'/Source',.75)['passed'])

    def test_nearest_unexpected_source_cannot_be_hidden(self):
        hits=[dict(collider='/Expected',z=.75,distance=.002),dict(collider='/Blocking',z=.751,distance=.001)]
        self.assertFalse(classify_hits(hits,[],'/Expected',.75)['passed'])
