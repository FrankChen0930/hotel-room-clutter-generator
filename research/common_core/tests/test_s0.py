from pathlib import Path
import unittest
from common_core.contracts import load_json
from common_core.room import Inputs
from common_core.planner import plan_requests

CODE=Path(__file__).resolve().parents[1]


class S0PolicyTests(unittest.TestCase):
    def test_policy_selects_states_without_per_scene_requirement_or_seed_recipe(self):
        catalog=load_json(CODE/'config/catalog.json');policy=load_json(CODE/'config/policy.json')
        for room in ['hotel705','yazhi']:
            inputs=Inputs(load_json(CODE/f'config/rooms/{room}.json'),catalog,policy,{}, {})
            for scenario in ['STAYOVER','CHECKOUT']:
                for seed in [706,707,708,99123]:
                    for level,expected in [('low',None),('medium','folded'),('high','loose')]:
                        plan=plan_requests(inputs,seed,scenario,level);towels=[r for r in plan['requests'] if r['category']=='towel']
                        self.assertEqual(len(towels),0 if expected is None else 1)
                        if towels:self.assertEqual(towels[0]['state_id'],expected)

    def test_selected_state_locators_and_geometry_are_distinct(self):
        entry=next(e for e in load_json(CODE/'config/catalog.json')['entries'] if e['asset_id']=='s0_towel')
        self.assertNotEqual(entry['states'][0]['usd_locator_or_native_prim'],entry['states'][1]['usd_locator_or_native_prim'])
        self.assertNotEqual(entry['states'][0]['physics_proxy']['geometry_hash'],entry['states'][1]['physics_proxy']['geometry_hash'])
