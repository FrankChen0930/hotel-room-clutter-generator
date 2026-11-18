import copy, json, tempfile, unittest
from pathlib import Path
from common_core.contracts import load_json, validate_contract, verify_source
from common_core.identity import sha256_file
from fixtures import profile

class ContractsTest(unittest.TestCase):
    def test_minimal_profile_valid(self):
        p=profile(); self.assertEqual(validate_contract(p,'RoomProfile'),p)
    def test_unknown_major_rejected(self):
        p=profile(); p['schema_version']='2.0'
        with self.assertRaisesRegex(ValueError,'SCHEMA_VERSION'): validate_contract(p,'RoomProfile')
    def test_source_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2]/'_common_core_runs') as d:
            p=Path(d)/'source'; p.write_bytes(b'locked')
            with self.assertRaisesRegex(ValueError,'SOURCE_HASH_MISMATCH'): verify_source(p,'0'*64)
            verify_source(p,sha256_file(p))
    def test_fixed_object_override_rejected(self):
        p=profile(); p['override_allowlist']=[dict(prim='/Room/Table',attributes=['xformOp:translate'])]
        with self.assertRaisesRegex(ValueError,'FIXED_OBJECT_OVERRIDE'): validate_contract(p,'RoomProfile')
    def test_fixed_descendant_override_rejected(self):
        p=profile(); p['override_allowlist']=[dict(prim='/Room/Table/Mesh',attributes=['visibility'])]
        with self.assertRaisesRegex(ValueError,'FIXED_OBJECT_OVERRIDE'): validate_contract(p,'RoomProfile')
    def test_json_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2]/'_common_core_runs') as d:
            p=Path(d)/'bad.json';p.write_text('{"x":NaN}')
            with self.assertRaisesRegex(ValueError,'NONFINITE'):load_json(p)
    def test_json_root_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2]/'_common_core_runs') as d:
            p=Path(d)/'bad.json';p.write_text('[]')
            with self.assertRaisesRegex(ValueError,'JSON_OBJECT'):load_json(p)
    def test_duplicate_key_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2]/'_common_core_runs') as d:
            p=Path(d)/'bad.json';p.write_text('{"seed":705,"seed":709}')
            with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):load_json(p)
