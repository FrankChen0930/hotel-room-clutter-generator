import copy
from pathlib import Path
import unittest
from common_core.sdk import load_usd
load_usd(Path('C:/isaac_sim'))
from common_core.room import load_inputs, prepare_room, resolve_locator
from common_core.contracts import validate_contract

CODE=Path(__file__).resolve().parents[1]


class RoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=load_inputs(CODE/'config/deployment.local.json','hotel705',require_policy=False)
        cls.cache=prepare_room(cls.inputs.profile,cls.inputs.bindings)

    def test_measured_three_supports_and_native_initial(self):
        self.assertEqual(set(self.cache.supports),{'desk','minibar','bench'})
        self.assertEqual(len(self.cache.native_initial),9)
        self.assertTrue(all(s['status']=='SUPPORTED' for s in self.cache.supports.values()))
        for native in self.cache.native_initial.values():
            self.assertEqual(len(native['world_matrix']),4);self.assertEqual(len(native['geometry_hash']),64)
        self.assertTrue(self.cache.obstacles['desk'])

    def test_native_external_catalog_and_authority(self):
        catalog=self.inputs.catalog;validate_contract(catalog,'Catalog')
        self.assertEqual(sum(e['origin']=='native' for e in catalog['entries']),9)
        self.assertTrue({'book','tissue','remote','bottle','can'}<={e['asset_id'] for e in catalog['entries'] if e['origin']=='external'})
        for entry in catalog['entries']:
            self.assertNotIn('asset_globally_physics_pass',entry)
            self.assertEqual(entry.get('qualification_refs',[]),[])
            for state in entry['states']:
                if entry['origin']=='native':self.assertEqual(state['physics_proxy']['capability'],'STATIC_ONLY')
                self.assertIn('state_transform',state)

    def test_tampered_source_hash_rejected(self):
        profile=copy.deepcopy(self.inputs.profile);profile['source']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH_MISMATCH'):prepare_room(profile,self.inputs.bindings)

    def test_tampered_collider_identity_rejected(self):
        profile=copy.deepcopy(self.inputs.profile);profile['supports'][0]['geometry_hash']='0'*64
        with self.assertRaisesRegex(ValueError,'SUPPORT_COLLIDER_IDENTITY'):prepare_room(profile,self.inputs.bindings)

    def test_missing_support_rejected(self):
        profile=copy.deepcopy(self.inputs.profile);profile['supports'][0]['collider']='/root/Missing'
        with self.assertRaisesRegex(ValueError,'SUPPORT_COLLIDER_MISSING'):prepare_room(profile,self.inputs.bindings)

    def test_coordinate_conversion_is_explicit(self):
        profile=copy.deepcopy(self.inputs.profile);profile['coordinates']['to_common'][3][0]=1
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_COORDINATE_CONVERSION'):prepare_room(profile,self.inputs.bindings)

    def test_logical_mount_and_path_escape(self):
        with self.assertRaisesRegex(ValueError,'MISSING_MOUNT'):resolve_locator(dict(mount='unknown',path='file'),self.inputs.bindings)
        with self.assertRaisesRegex(ValueError,'SOURCE_PATH'):resolve_locator(dict(mount='room_hotel',path='../file'),self.inputs.bindings)

    def test_geometry_cache_key_binds_profile(self):
        profile=copy.deepcopy(self.inputs.profile);profile['profile_version']='1.0-test'
        other=prepare_room(profile,self.inputs.bindings)
        self.assertNotEqual(self.cache.cache_key,other.cache_key)
        self.assertEqual(self.cache.native_initial,other.native_initial)
