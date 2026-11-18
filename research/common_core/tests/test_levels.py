import copy
from pathlib import Path
import tempfile
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.contracts import load_json
from common_core.identity import content_digest
from common_core.metrics import placement_metrics,composed_metrics,check_targets,summarize
from common_core.room import load_inputs,prepare_room,RoomCache
from common_core.planner import plan_requests
from common_core.placer import place_requests
from common_core.writer import write_scene
from common_core.manifest import build_manifest
from common_core.paths import RUN_ROOT

CODE=Path(__file__).resolve().parents[1]


class LevelMetricsTests(unittest.TestCase):
    def test_composed_metrics_equal_calibration_method_in_both_rooms(self):
        for room_id in ['hotel705','yazhi']:
            inputs=load_inputs(CODE/'config/deployment.local.json',room_id);room=prepare_room(inputs.profile,inputs.bindings)
            plan=plan_requests(inputs,7001,'CHECKOUT','high');placed=place_requests(plan,room,inputs.catalog)
            self.assertEqual(placed['status'],'PASS')
            with tempfile.TemporaryDirectory(dir=RUN_ROOT) as temp:
                scene=Path(temp)/'scene.usda';write_scene(scene,inputs,placed);manifest=build_manifest(inputs,plan,placed,scene,'metrics-fixture')
                expected=placement_metrics(placed['objects'],room,inputs.catalog);actual=composed_metrics(scene,manifest,room,inputs.catalog)
                self.assertAlmostEqual(expected['coverage'],actual['coverage'],places=9)
                self.assertEqual(actual['state_counts'],expected['state_counts'])
                self.assertGreaterEqual(actual['occupied_supports'],3)
                self.assertFalse(check_targets(actual,plan['targets'],inputs.policy,room_id,'CHECKOUT','high',content_digest(inputs.profile),content_digest(inputs.catalog)))
                manifest['objects'][0]['footprint']=[[0,0],[100,0],[100,100],[0,100]]
                self.assertAlmostEqual(actual['coverage'],composed_metrics(scene,manifest,room,inputs.catalog)['coverage'],places=12)

    def test_overlapping_projected_footprints_cannot_inflate_sum(self):
        support=dict(allowed_region=[[-1,-1],[1,-1],[1,1],[-1,1]])
        room=RoomCache('k',Path('unused'),'id',{'top':support},{'top':[]},{})
        row=dict(footprint=[[0,0],[.1,0],[.1,.1],[0,.1]],support_id='top',category='cup',asset_id='cup',state_id='default')
        with self.assertRaisesRegex(ValueError,'METRICS_PROJECTED_FOOTPRINT_OVERLAP'):summarize([row,copy.deepcopy(row)],room)

    def test_frozen_denominator_and_coverage_are_hard(self):
        inputs=load_inputs(CODE/'config/deployment.local.json','yazhi');room=prepare_room(inputs.profile,inputs.bindings)
        plan=plan_requests(inputs,7001,'STAYOVER','low');placed=place_requests(plan,room,inputs.catalog)
        metrics=placement_metrics(placed['objects'],room,inputs.catalog)
        args=(plan['targets'],inputs.policy,'yazhi','STAYOVER','low',content_digest(inputs.profile),content_digest(inputs.catalog))
        poisoned=copy.deepcopy(metrics);poisoned['coverage']=1.;self.assertIn('COVERAGE_HARD_TARGET',check_targets(poisoned,*args))
        poisoned=copy.deepcopy(metrics);poisoned['denominator_m2']*=2;self.assertIn('FROZEN_DENOMINATOR',check_targets(poisoned,*args))

    def test_original_count_ranges_and_frozen_policy(self):
        policy=load_json(CODE/'config/policy.json');self.assertTrue(policy['release_frozen'])
        self.assertEqual(policy['levels']['low']['count_ranges']['STAYOVER'],[5,6])
        self.assertEqual(policy['levels']['high']['count_ranges']['CHECKOUT'],[16,18])
        self.assertEqual([policy['levels'][l]['spread']['occupied_support_min'] for l in ['low','medium','high']],[1,2,3])
