import unittest
from common_core.native_validation import proxy_supported


class ProxyTests(unittest.TestCase):
    def test_only_implemented_shape_paths_can_dispatch(self):
        self.assertTrue(proxy_supported('box'));self.assertTrue(proxy_supported('cylinder'))
        for kind in ['none','convex','compound','mesh',None]:self.assertFalse(proxy_supported(kind))
