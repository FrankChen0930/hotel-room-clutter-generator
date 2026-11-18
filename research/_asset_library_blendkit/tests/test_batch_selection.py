import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from batch_selection import choose
def item(name,base='id',license='royalty_free',free=True):return dict(name=name,assetBaseId=base,license=license,isFree=free,canDownload=True,assetType='model')
class SelectionTests(unittest.TestCase):
    def test_guest_keywords_do_not_admit_fixtures(self):
        for name,category in [('Modern Floating Makeup Vanity Dresser','toiletry'),('USB charger socket','electronics'),('Hikivision IP camera','electronics')]:
            self.assertIsNone(choose([item(name)],category)[0])
    def test_furniture_and_paid_hits_rejected(self):
        index,_=choose([item('suitcase',free=False),item('luggage trolley'),item('travel suitcase','ok')],'luggage')
        self.assertEqual(index,2)
    def test_cc0_preferred_and_duplicates_excluded(self):
        r=[item('realistic leather shoes','a'),item('sneaker','b','cc_zero')]
        self.assertEqual(choose(r,'footwear')[0],1)
        self.assertEqual(choose(r,'footwear',{'b'})[0],0)
    def test_unknown_or_extractability_not_inferred(self):
        self.assertIsNone(choose([item('towel',license='unknown'),item('towel rack')],'towel')[0])
    def test_wrong_semantics_rejected(self):
        self.assertIsNone(choose([item('sports car')],'electronics')[0])
    def test_specialized_safety_clothing_deferred(self):
        self.assertIsNone(choose([item('life jacket')],'clothing')[0])
    def test_parsed_size_is_kib_not_bytes(self):
        a=item('travel suitcase');a['filesSize']=842416
        self.assertIsNone(choose([a],'luggage')[0])
