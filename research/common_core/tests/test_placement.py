from pathlib import Path
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.room import RoomCache
from common_core.placer import place_requests
from fixtures import catalog,matrix


class PlacementTests(unittest.TestCase):
    def fixture(self):
        asset=catalog();asset['entries'][0]['states'][0]['state_transform']=matrix()
        support=dict(status='SUPPORTED',shape='polygon',polygon=[[-1,-1],[1,-1],[1,1],[-1,1]],
                     allowed_region=[[-1,-1],[1,-1],[1,1],[-1,1]],edge_margin_m=.01,z=0.)
        room=RoomCache('key',Path('unused'),'identity',{'desk':support},{'desk':[]},{})
        req=dict(request_id='guest/cup/0',asset_id='cup',state_id='clean',origin='external',source_object_id=None,
                 semantic_state=dict(ownership='GUEST',action_policy='DO_NOT_TOUCH'),allowed_support_ids=['desk'])
        plan=dict(seed=709,scenario='STAYOVER',requests=[req],budgets=dict(max_supports=1,samples_per_support=10,max_samples_per_request=10))
        return plan,room,asset

    def test_deterministic_placement_and_gap(self):
        plan,room,assets=self.fixture();a=place_requests(plan,room,assets);b=place_requests(plan,room,assets)
        self.assertEqual(a,b);self.assertEqual(a['status'],'PASS');self.assertAlmostEqual(a['objects'][0]['expected_bounds'][0][2],.001)

    def test_obstacle_and_budget_exhaustion_is_not_pass(self):
        plan,room,assets=self.fixture();room.obstacles['desk'].append(dict(prim='/Fixed',bounds=[[-2,-2,-1],[2,2,2]]))
        result=place_requests(plan,room,assets);self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['failure']['reason'],'PLACEMENT_EXHAUSTED');self.assertEqual(result['sampling'][0]['samples'],10)

    def test_off_support_and_forbidden_region(self):
        plan,room,assets=self.fixture();room.supports['desk']['allowed_region']=[[5,5],[6,5],[6,6],[5,6]]
        self.assertEqual(place_requests(plan,room,assets)['status'],'FAIL')
        plan,room,assets=self.fixture();room=RoomCache(room.cache_key,room.source_path,room.source_identity,room.supports,room.obstacles,room.native_initial,({'bounds':[[-2,-2,-1],[2,2,2]]},))
        result=place_requests(plan,room,assets);self.assertEqual(result['status'],'FAIL')
        self.assertGreater(result['sampling'][0]['rejections']['forbidden_region'],0)
        self.assertEqual(sum(result['sampling'][0]['rejections'].values()),10)
