import copy
from pathlib import Path
import unittest
from common_core.contracts import load_json
from common_core.room import Inputs
from common_core.planner import plan_requests
from fixtures import profile

CODE=Path(__file__).resolve().parents[1]


class PlannerTests(unittest.TestCase):
    def inputs(self):
        p=load_json(CODE/'config/rooms/hotel705.json')
        return Inputs(p,load_json(CODE/'config/catalog.json'),load_json(CODE/'config/policy.json'),{}, {})

    def test_new_seeds_six_combinations_and_strict_counts(self):
        inputs=self.inputs()
        for seed in [705,706,709,123456,-2147483648,2147483647]:
            for scenario in ['STAYOVER','CHECKOUT']:
                counts=[]
                for level in ['low','medium','high']:
                    a=plan_requests(inputs,seed,scenario,level);b=plan_requests(inputs,seed,scenario,level)
                    self.assertEqual(a,b);counts.append(len(a['requests']))
                    self.assertEqual(a['targets']['count'],len(a['requests']))
                    self.assertEqual(len({r['request_id'] for r in a['requests']}),len(a['requests']))
                self.assertLess(counts[0],counts[1]);self.assertLess(counts[1],counts[2])

    def test_semantics_and_required_categories(self):
        for scenario in ['STAYOVER','CHECKOUT']:
            inputs=self.inputs();plan=plan_requests(inputs,709,scenario,'high')
            present={r['category'] for r in plan['requests']}
            self.assertTrue(set(inputs.policy['scenarios'][scenario]['required_categories'])<=present)
            native=[]
            for request in plan['requests']:
                sem=request['semantic_state']
                if sem['ownership'] in ['GUEST','UNKNOWN']:self.assertEqual(sem['action_policy'],'DO_NOT_TOUCH')
                if request['origin']=='native':native.append(request['asset_id'])
                if sem['task_role']=='DECLARED_TRASH':self.assertIn('EXPLICIT_SYNTHETIC',sem['state_evidence'])
            self.assertEqual(len(native),len(set(native)))

    def test_source_config_is_not_mutated(self):
        inputs=self.inputs();before=copy.deepcopy(inputs)
        plan_requests(inputs,705,'CHECKOUT','high');self.assertEqual(inputs,before)

    def test_unknown_parameters_rejected(self):
        for args in [(True,'STAYOVER','low'),(1,'UNKNOWN','low'),(1,'STAYOVER','extreme')]:
            with self.assertRaises(ValueError):plan_requests(self.inputs(),*args)

    def test_no_required_category_silent_degradation(self):
        inputs=self.inputs();inputs.catalog['entries']=[e for e in inputs.catalog['entries'] if e['category']!='book']
        with self.assertRaisesRegex(ValueError,'REQUIRED_CATEGORY_UNAVAILABLE'):plan_requests(inputs,706,'STAYOVER','low')

    def test_scenario_has_explicit_distinct_semantics(self):
        inputs=self.inputs();a=plan_requests(inputs,706,'STAYOVER','high');b=plan_requests(inputs,706,'CHECKOUT','high')
        self.assertNotEqual({r['category']:r['semantic_state']['task_role'] for r in a['requests']},
                            {r['category']:r['semantic_state']['task_role'] for r in b['requests']})
