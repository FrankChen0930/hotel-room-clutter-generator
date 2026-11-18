from copy import deepcopy
import unittest
from unittest.mock import patch
from common_core.identity import content_digest
from common_core.qualification import verify


class QualificationTests(unittest.TestCase):
    def test_changed_exact_identity_invalidates_old_pass(self):
        identity = dict(case_directory='fixture', source='a', asset_state='a', collider='a',
                        support_transform=[0,0,0], pose=[0,0,0], runtime='a', physics='a', evidence='a')
        record = dict(execution='EXECUTED', outcome='PASS', identity=identity, fingerprint=content_digest(identity))
        with patch('common_core.qualification.assess', return_value=identity):
            self.assertTrue(verify(record, None))
        for key in identity:
            changed = deepcopy(identity); changed[key] = 'changed'
            with self.subTest(key=key), patch('common_core.qualification.assess', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'STALE'): verify(record, None)

    def test_changed_record_cannot_keep_fingerprint_or_skip_execution(self):
        record = dict(execution='EXECUTED', outcome='PASS', identity=dict(case_directory='fixture'), fingerprint='incorrect')
        with self.assertRaisesRegex(ValueError, 'FINGERPRINT'): verify(record, None)
        record['execution']='RECORDED'
        with self.assertRaisesRegex(ValueError, 'RECORD'): verify(record, None)
