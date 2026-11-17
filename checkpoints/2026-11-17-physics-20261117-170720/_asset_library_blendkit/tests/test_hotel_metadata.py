from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from hotel_metadata import enrich

def asset(category):return dict(name='Travel object',category=category,status='BLOCKED',situations=['stayover_personal'],physics=dict(mode='STATIC_ONLY'))
class RoboticsMetadataTests(unittest.TestCase):
    def test_backpack_appearance_does_not_grant_soft_physics_or_manipulation(self):
        a=enrich(asset('bag'));self.assertEqual(a['object_form'],'soft-like');self.assertEqual(a['robotics_relevance'],'perception_candidate');self.assertFalse(a['deformation_solved'])
    def test_soft_research_label_is_not_acceptance(self):
        a=enrich(asset('clothing'));self.assertEqual(a['robotics_relevance'],'soft_object_research_candidate');self.assertEqual(a['quality_decision'],'blocked')
    def test_local_acceptance_separate_from_rights_block(self):
        a=asset('bag');a['local_qualification']=dict(outcome='PASS');a=enrich(a)
        self.assertEqual(a['quality_decision'],'accepted');self.assertEqual(a['status'],'BLOCKED')
