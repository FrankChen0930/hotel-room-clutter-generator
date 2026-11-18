import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest

from common_core.identity import (canonical_json, content_digest, rng_for,
                                  rng_seed, stable_request_id, validate_seed, state_digest)
from fixtures import manifest


class IdentityTests(unittest.TestCase):
    def test_state_digest_authority_and_deployment_independence(self):
        obj=manifest(); original=state_digest(obj)
        obj['run_id']='different';obj['attempt_id']='a001';obj['environment']={'cwd':'C:/new location'}
        obj['inputs']['deployment']={'room':'D:/remounted'}
        obj['objects'][0]['after']['semantic_state']='proposal only'
        obj['evidence_refs']=[{'not':'part of state'}]
        self.assertEqual(original,state_digest(obj))
        obj['objects'][0]['effective']['world_matrix'][3][0]=.01
        self.assertNotEqual(original,state_digest(obj))
    def test_signed32_and_legacy_recipe_seeds(self):
        for seed in (-2147483648, -1, 0, 705, 709, 2147483647):
            self.assertEqual(validate_seed(seed), seed)
            self.assertEqual(rng_for(seed, 'placement', 'cup/0').random(),
                             rng_for(seed, 'placement', 'cup/0').random())

    def test_invalid_seeds_rejected(self):
        for seed in (-2147483649, 2147483648, True, 1.0, '705', None):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, 'SEED_SIGNED32'):
                validate_seed(seed)

    def test_exact_v1_derivation(self):
        payload = json.dumps(['cc-rng-v1', 709, 'placement', 'guest/cup/0', 0],
                             sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        expected = int.from_bytes(hashlib.sha256(payload).digest()[:16], 'big')
        self.assertEqual(rng_seed(709, 'placement', 'guest/cup/0'), expected)
        self.assertEqual(rng_for(709, 'placement', 'guest/cup/0').random(), random.Random(expected).random())

    def test_unrelated_request_does_not_consume_stream(self):
        a = rng_for(705, 'placement', 'guest/cup/0')
        first = a.random()
        for _ in range(100):
            rng_for(705, 'placement', 'unrelated/book/99').random()
        self.assertEqual(first, rng_for(705, 'placement', 'guest/cup/0').random())
        self.assertNotEqual(first, rng_for(705, 'repair', 'guest/cup/0').random())
        self.assertNotEqual(first, rng_for(705, 'placement', 'guest/cup/0', 1).random())

    def test_count_quantile_same_across_levels(self):
        q = rng_for(705, 'count/STAYOVER', 'scene').random()
        counts = [lo + int(q * (hi-lo+1)) for lo, hi in [(5, 6), (8, 9), (12, 13)]]
        self.assertLess(counts[0], counts[1]); self.assertLess(counts[1], counts[2])

    def test_canonical_and_nonfinite(self):
        self.assertEqual(content_digest({'b': 1, 'a': 2}), content_digest({'a': 2, 'b': 1}))
        with self.assertRaises(ValueError): canonical_json({'bad': float('nan')})

    def test_stream_arguments_rejected(self):
        for args in [(1, '', 'x', 0), (1, 'placement', '', 0), (1, 'placement', 'x', -1),
                     (1, 'placement', 'x', True)]:
            with self.subTest(args=args), self.assertRaises(ValueError): rng_seed(*args)

    def test_stable_id(self):
        self.assertEqual(stable_request_id('guest', 'cup', 2), 'guest/cup/2')
        with self.assertRaises(ValueError): stable_request_id('guest/other', 'cup', 0)

    def test_cwd_and_python_hash_seed_independence(self):
        code_root = Path(__file__).resolve().parents[1]
        code = ('import sys;sys.path.insert(0,sys.argv[1]);'
                'from common_core.identity import rng_seed,content_digest;'
                'print(rng_seed(709,"placement","guest/cup/0"));'
                'print(content_digest({"policy":"a","source":"b"}))')
        outputs=[]
        for cwd, hashseed in [(code_root, '1'), (code_root.parent, '53')]:
            result=subprocess.run([sys.executable, '-B', '-c', code, str(code_root)], cwd=cwd,
                                  env={**os.environ, 'PYTHONHASHSEED': hashseed}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        self.assertEqual(*outputs)
