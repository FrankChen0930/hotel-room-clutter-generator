from pathlib import Path
import unittest
from common_core.contracts import load_json,validate_contract,verify_source

CODE=Path(__file__).resolve().parents[1]


class S0SelectionTests(unittest.TestCase):
    def test_two_adopted_distinct_static_mesh_states(self):
        catalog=validate_contract(load_json(CODE/'config/catalog.json'),'Catalog')
        towel=next(e for e in catalog['entries'] if e['asset_id']=='s0_towel')
        self.assertEqual(towel['category'],'towel');self.assertEqual({s['state_id'] for s in towel['states']},{'folded','loose'})
        self.assertEqual(len({s['sha256'] for s in towel['states']}),2)
        self.assertEqual(len({s['physics_proxy']['geometry_hash'] for s in towel['states']}),2)
        for state in towel['states']:
            verify_source(CODE.parent/'YAZHI-TWIN'/state['usd_locator_or_native_prim']['path'],state['sha256'])
            self.assertEqual(state['physics_proxy']['capability'],'STATIC_ONLY')
            self.assertEqual(state['physics_proxy']['kind'],'none')
            self.assertGreaterEqual(state['support_envelope']['clearance_m'],.0005)

    def test_adopted_geometry_fits_existing_planar_region_dimensions(self):
        catalog=load_json(CODE/'config/catalog.json');towel=next(e for e in catalog['entries'] if e['asset_id']=='s0_towel')
        for state in towel['states']:
            lo,hi=state['visual_bounds'];self.assertLess(hi[0]-lo[0],.464);self.assertLess(hi[1]-lo[1],.464)
