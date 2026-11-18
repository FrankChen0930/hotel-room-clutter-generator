import copy
import unittest
from common_core.contracts import validate_contract
from fixtures import catalog, manifest, policy, profile


class VersionedContractsTests(unittest.TestCase):
    def reject(self, obj, kind, reason):
        with self.assertRaisesRegex(ValueError, reason): validate_contract(obj,kind)

    def test_all_contracts_valid(self):
        for builder,kind in [(profile,'RoomProfile'),(catalog,'Catalog'),(policy,'Policy'),(manifest,'Manifest')]:
            with self.subTest(kind=kind): self.assertEqual(validate_contract(builder(),kind),builder())

    def test_unknown_major_all_kinds(self):
        for builder,kind in [(profile,'RoomProfile'),(catalog,'Catalog'),(policy,'Policy'),(manifest,'Manifest')]:
            obj=builder();obj['schema_version']='99.0';self.reject(obj,kind,'SCHEMA_VERSION')

    def test_missing_required_contract_fields(self):
        for builder,kind,key in [(profile,'RoomProfile','coordinates'),(catalog,'Catalog','entries'),
                                 (policy,'Policy','budgets'),(manifest,'Manifest','objects')]:
            obj=builder();del obj[key];self.reject(obj,kind,'MISSING_FIELD')

    def test_source_escape_and_malformed_structure(self):
        for path in ['../secret.usd','C:/secret.usd','https://host/a.usd','a/../../b.usd',r'..\b.usd']:
            obj=profile();obj['source']['path']=path;self.reject(obj,'RoomProfile','SOURCE_PATH')
        obj=profile();obj['source_objects']='bad';self.reject(obj,'RoomProfile','TYPE')

    def test_source_mobility_and_override_whitelist(self):
        obj=profile();obj['source_objects'][0]['mobility']='FLYING';self.reject(obj,'RoomProfile','MOBILITY')
        obj=profile();obj['override_allowlist']=[dict(prim='/Room',attributes=['visibility'])]
        self.reject(obj,'RoomProfile','FIXED_OBJECT_OVERRIDE')
        obj=profile();obj['override_allowlist']=[dict(prim='/Room/Other',attributes=['visibility'])]
        self.reject(obj,'RoomProfile','OVERRIDE_NOT_MOVABLE')

    def test_duplicate_ids(self):
        obj=catalog();obj['entries'].append(copy.deepcopy(obj['entries'][0]));self.reject(obj,'Catalog','DUPLICATE_ID')
        obj=profile();obj['supports'].append(copy.deepcopy(obj['supports'][0]));self.reject(obj,'RoomProfile','DUPLICATE_ID')

    def test_catalog_state_sha_and_proxy_capability(self):
        obj=catalog();obj['entries'][0]['states'][0]['sha256']='bad';self.reject(obj,'Catalog','SHA256')
        obj=catalog();obj['entries'][0]['states'][0]['physics_proxy']['capability']='DYNAMIC_CANDIDATE'
        self.reject(obj,'Catalog','PROXY_NONE_DYNAMIC')
        obj=catalog();obj['entries'][0]['asset_globally_physics_pass']=True;self.reject(obj,'Catalog','GLOBAL_QUALIFICATION')

    def test_native_catalog_uses_geometry_signature(self):
        obj=catalog();entry=obj['entries'][0];entry['origin']='native';entry['source_locator']='/Room/Cup'
        entry['states'][0]['usd_locator_or_native_prim']='/Room/Cup'
        self.assertEqual(validate_contract(obj,'Catalog'),obj)

    def test_policy_nonoverlap_and_bounded_budgets(self):
        obj=policy();obj['levels']['high']['count_ranges']['STAYOVER']=[8,13]
        self.reject(obj,'Policy','COUNT_RANGE_OVERLAP')
        for key,value in [('native_retries',2),('max_supports',4),('samples_per_support',801),('repair_passes',2),('max_samples_per_request',4801)]:
            obj=policy();obj['budgets'][key]=value;self.reject(obj,'Policy','BUDGET')

    def test_manifest_authority_and_native_before(self):
        obj=manifest();del obj['objects'][0]['effective'];self.reject(obj,'Manifest','MISSING_FIELD')
        obj=manifest();obj['objects'][0]['effective']['world_matrix']=[[1]];self.reject(obj,'Manifest','MATRIX')
        obj=manifest();obj['objects'][0]['origin']='native';self.reject(obj,'Manifest','NATIVE_MAPPING')
        obj=manifest();obj['objects'][0]['before']['world_matrix']=[[1]];self.reject(obj,'Manifest','EXTERNAL_BEFORE')
        obj=manifest();obj['objects'][0]['soft']={};self.reject(obj,'Manifest','AMBIGUOUS_STATE')

    def test_manifest_evidence_not_run_cannot_pass(self):
        obj=manifest();obj['evidence_refs']=[dict(kind='physics',uri='physics.json',sha256='a'*64,
            execution='NOT_RUN',outcome='PASS',scope={},target_state_digest='e'*64,producer_identity={})]
        self.reject(obj,'Manifest','EVIDENCE_NOT_RUN_PASS')

    def test_seed_float_nan_and_matrix_nonfinite(self):
        obj=manifest();obj['inputs']['seed']=True;self.reject(obj,'Manifest','SEED_SIGNED32')
        obj=profile();obj['coordinates']['to_common'][0][0]=float('inf');self.reject(obj,'RoomProfile','NONFINITE')
