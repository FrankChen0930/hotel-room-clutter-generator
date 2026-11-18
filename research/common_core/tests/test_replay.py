import copy
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from unittest.mock import patch
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.room import load_inputs
from common_core.replay import load_manifest,replay_manifest
from common_core.paths import RUN_ROOT

CODE=Path(__file__).resolve().parents[1]


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from common_core.room import prepare_room
        from common_core.planner import plan_requests
        from common_core.placer import place_requests
        from common_core.writer import write_scene
        from common_core.manifest import build_manifest,seal_manifest,write_json_new
        cls.inputs=load_inputs(CODE/'config/deployment.local.json','hotel705')
        cls.temp=tempfile.TemporaryDirectory(dir=RUN_ROOT);root=Path(cls.temp.name)
        plan=plan_requests(cls.inputs,706,'STAYOVER','low');room=prepare_room(cls.inputs.profile,cls.inputs.bindings)
        placed=place_requests(plan,room,cls.inputs.catalog)
        if placed['status']!='PASS':raise AssertionError('Replay fixture placement failed')
        scene=root/'scene.usda';write_scene(scene,cls.inputs,placed)
        manifest=build_manifest(cls.inputs,plan,placed,scene,'replay-fixture')
        evidence=root/'validation';evidence.mkdir();write_json_new(evidence/'fixture.json',dict(scope='replay fixture only'))
        from common_core.identity import sha256_file
        manifest['evidence_refs']=[dict(kind='fixture',uri='validation/fixture.json',sha256=sha256_file(evidence/'fixture.json'),
            execution='EXECUTED',outcome='PASS',scope='fixture setup',target_state_digest=manifest['scene']['state_digest'],producer_identity={})]
        cls.source=root/'manifest.json';seal_manifest(manifest,cls.source)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_no_rng_and_relocated_composed_state(self):
        manifest=load_manifest(self.source,self.inputs)
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp,patch('random.Random',side_effect=AssertionError('RNG forbidden')):
            report=replay_manifest(manifest,Path(temp)/'relocated output',self.inputs,self.source.parent/'scene.usda')
            self.assertEqual(report['outcome'],'PASS',report['errors']);self.assertLessEqual(report['max_matrix_error'],1e-8)

    def test_tampered_state_rejected(self):
        manifest=json.loads(self.source.read_text());manifest['objects'][0]['effective']['world_matrix'][3][0]+=.01
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            path=Path(temp)/'manifest.json';path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'STATE_DIGEST_MISMATCH'):load_manifest(path,self.inputs)

    def test_tampered_evidence_rejected(self):
        manifest=json.loads(self.source.read_text());manifest['evidence_refs'][0]['sha256']='0'*64
        with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
            root=Path(temp);shutil.copytree(self.source.parent/'validation',root/'validation')
            path=root/'manifest.json';path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'EVIDENCE_HASH_MISMATCH'):load_manifest(path,self.inputs)
