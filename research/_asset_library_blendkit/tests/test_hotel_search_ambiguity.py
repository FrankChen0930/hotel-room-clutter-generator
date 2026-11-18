import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from batch_selection import assess

class HotelSearchAmbiguityTests(unittest.TestCase):
    def check_name(self,name,category):
        return assess(dict(assetBaseId='example',displayName=name,assetType='model',isFree=True,canDownload=True,license='cc_zero'),category)
    def test_real_collector_false_positives_are_excluded(self):
        for name,category in [('Windsock (Procedurally Animated)','clothing'),('Windsock mast','clothing'),('Royal Bank Cash Game chips','food'),('Nile Club Poker Chips, Ceramic','food'),('Chips Blenderkit special edition II','food'),('Snack Server','food'),('Snacks for supermarket gondulas','food'),('Scan Broken Hard Hat','clothing'),('Suitcase strapped to a bunch of ballons','luggage')]:
            self.assertIsNone(self.check_name(name,category)[0],name)
    def test_everyday_guest_items_survive(self):
        for name,category in [('White Sport Socks','clothing'),('Stack of folded t-shirts','clothing'),('Potato chips packet','food'),('Quilted Handbag','bag'),('Laptop charger','electronics')]:
            self.assertIsNotNone(self.check_name(name,category)[0],name)

if __name__=='__main__':unittest.main()
