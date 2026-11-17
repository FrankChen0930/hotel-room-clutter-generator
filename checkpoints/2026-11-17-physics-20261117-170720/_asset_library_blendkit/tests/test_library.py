import copy
import sys
import tempfile
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import library as lib

def candidate():
    return dict(asset_id='bk-test',status='DISCOVERED',last_completed_stage='DISCOVERED',category='book',
        source=dict(asset_base_id='755a9a16-d738-44ab-9ab6-07d35db05e47',url='https://www.blendkit.com/asset-gallery-detail/755a9a16-d738-44ab-9ab6-07d35db05e47/'),
        rights=dict(license='CC0',internal_use=None,extractable_usd=None,redistribution=None,decision='PENDING'),
        usd={},evidence={},physics=dict(mode='STATIC_ONLY'))

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.old=lib.ROOT; lib.ROOT=Path(self.temp.name)
    def tearDown(self):
        lib.ROOT=self.old; self.temp.cleanup()
    def ref(self,name,content):
        p=lib.ROOT/name; lib.write(p,content); return dict(path=name,sha256=lib.sha(p))
    def complete(self):
        a=candidate(); a['status']=a['last_completed_stage']='GENERATION_READY'
        a['source'].update(version_id='v1',acquisition_method='OFFICIAL_ADDON',
            original_file=self.ref('source.blend',{}))
        a['source']['original_download_files']=[self.ref('official-original.blend',{})]
        a['source']['receipt']=self.ref('receipt.json',dict(asset_base_id=a['source']['asset_base_id'],version_id='v1',original_sha256=a['source']['original_file']['sha256']))
        a['geometry_identity']='geometry-one'; a['appearance_family']='paperback'
        a['usd']=self.ref('asset.usdc',{})
        a['rights'].update(internal_use=True,extractable_usd=True,redistribution=True,decision='CLEARED',decision_evidence=self.ref('rights.json',{}))
        for k in ('conversion','integrity','static','native_render','visual','support','catalog','replay'):
            report=dict(outcome='PASS',usd_sha256=a['usd']['sha256'])
            if k=='visual': report['reviewer']='unit-test-fixture'
            if k=='native_render': report['images']=[self.ref('image.png',{})]
            if k=='integrity': report['dependencies']=[self.ref('texture.png',{})]
            a['evidence'][k]=self.ref(k+'.json',report)
        return a
    def test_url_and_duplicate_identity(self):
        a=candidate()
        with self.assertRaisesRegex(ValueError,'DUPLICATE_SOURCE_ID'): lib.validate([a,copy.deepcopy(a)])
        a['source']['url']='https://elsewhere.test/'+a['source']['asset_base_id']
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_SOURCE'): lib.validate([a])
    def test_no_progress_from_urls_or_unknown_license(self):
        a=candidate(); a['status']=a['last_completed_stage']='GENERATION_READY'
        r=lib.summarize([a]); self.assertEqual(r['acquired'],0); self.assertEqual(r['generation_ready'],0)
        self.assertIn('EXTRACTABLE_USD_RIGHTS_UNCLEARED',r['invalid_ready']['bk-test'])
    def test_file_mutation_invalidates_qualification(self):
        a=self.complete(); self.assertEqual(lib.summarize([a])['generation_ready'],1)
        (lib.ROOT/'asset.usdc').write_text('changed')
        self.assertIn('USD_MISSING_OR_CHANGED',lib.gate_errors(a))
    def test_changed_texture_or_dependency_requires_integrity_rerun(self):
        a=self.complete(); (lib.ROOT/'texture.png').write_text('changed')
        self.assertIn('DEPENDENCY_MISSING_OR_CHANGED',lib.gate_errors(a))
    def test_forged_or_mismatched_acquisition_receipt_rejected(self):
        a=self.complete(); a['source']['receipt']=self.ref('receipt.json',dict(asset_base_id='other'))
        self.assertFalse(lib.acquired(a))
    def test_stale_report_and_missing_native_image(self):
        a=self.complete(); a['evidence']['static']=self.ref('stale.json',dict(outcome='PASS',usd_sha256='other'))
        (lib.ROOT/'image.png').unlink()
        self.assertIn('STATIC_NOT_PASS_OR_STALE',lib.gate_errors(a)); self.assertIn('NATIVE_IMAGE_CHANGED',lib.gate_errors(a))
    def test_variants_not_counted_twice(self):
        a=self.complete(); b=copy.deepcopy(a); b['asset_id']='variant'
        b['source']['asset_base_id']='557705f1-ef41-4a8c-9238-4a05f2cec153'
        b['source']['url']='https://www.blendkit.com/asset-gallery-detail/'+b['source']['asset_base_id']+'/'
        self.assertEqual(lib.summarize([a,b])['generation_ready'],1)
    def test_outside_path_rejected(self):
        self.assertFalse(lib.artifact_ok(dict(path='../outside',sha256='x')))
        self.assertFalse(lib.artifact_ok(None))
    def test_s0_geometry_variant_not_independent(self):
        a=self.complete(); a['variant_of']='root-asset'; a['geometry_identity']='different-s0-geometry'
        self.assertEqual(lib.summarize([a])['generation_ready'],0)
    def test_local_test_not_blocked_by_generator_or_public_rights(self):
        a=self.complete(); a['status']='BLOCKED'
        a['rights'].update(extractable_usd=None,redistribution=None,decision='PENDING',
            local_test_scope='CONTROLLED_WORKSPACE_NO_DISTRIBUTION',local_test_evidence=self.ref('local_test.json',dict(authorized=True)))
        self.assertEqual(lib.gate_errors(a,scope='local'),[])
        self.assertIn('EXTRACTABLE_USD_RIGHTS_UNCLEARED',lib.gate_errors(a))
        s=lib.summarize([a]); self.assertEqual(s['local_technical_ready'],1)
        self.assertEqual(s['generation_ready'],0); self.assertEqual(s['public_starter'],0)
    def test_local_test_still_requires_internal_rights_and_evidence(self):
        a=self.complete();a['rights'].update(internal_use=None,local_test_scope='CONTROLLED_WORKSPACE_NO_DISTRIBUTION')
        self.assertIn('LOCAL_TECHNICAL_TEST_NOT_AUTHORIZED',lib.gate_errors(a,scope='local'))
    def test_original_official_download_hash_required(self):
        a=self.complete();a['source']['original_download_files']=[]
        self.assertFalse(lib.acquired(a))
        a=self.complete();(lib.ROOT/'official-original.blend').write_text('modified')
        self.assertFalse(lib.acquired(a))

if __name__=='__main__':unittest.main()
