import json
from pathlib import Path
import tempfile
import unittest
from common_core.assessment import expand_tiers,TIERS
from common_core.batch import execute_batch,validate_spec


class CliTests(unittest.TestCase):
    def test_batch_retains_failed_case_and_runs_next_without_seed_change(self):
        root=Path(__file__).resolve().parents[2]/'_common_core_runs'
        with tempfile.TemporaryDirectory(dir=root) as temp:
            calls=[]
            def runner(argv):
                calls.append(argv);return 4 if len(calls)==1 else 0
            spec=dict(schema='Batch/1',cases=[dict(case_key='case'+str(i),room='room',scenario='STAYOVER',level='low',seed=706+i) for i in range(2)])
            out=Path(temp)/'batch';self.assertEqual(execute_batch(spec,Path('config.json'),out,runner),5)
            index=json.loads((out/'batch_index.json').read_text())
            self.assertEqual([r['exit_code'] for r in index['cases']],[4,0])
            self.assertEqual([a[a.index('--seed')+1] for a in calls],['706','707'])
            with self.assertRaisesRegex(ValueError,'OUTPUT_'):execute_batch(spec,Path('config.json'),out,runner)

    def test_invalid_keys_duplicate_and_seed_rejected_before_outputs(self):
        case=dict(case_key='valid',room='room',scenario='STAYOVER',level='low',seed=706)
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):validate_spec(dict(schema='Batch/1',cases=[case,case]))
        with self.assertRaisesRegex(ValueError,'CASE_KEY'):validate_spec(dict(schema='Batch/1',cases=[dict(case,case_key='../escape')]))
        with self.assertRaises(ValueError):validate_spec(dict(schema='Batch/1',cases=[dict(case,seed=2**40)]))

    def test_all_is_explicit_and_unknown_tiers_rejected(self):
        self.assertEqual(expand_tiers('all'),list(TIERS))
        self.assertIn('physics',expand_tiers('all'))
        for value in ['static,all','static,static','unknown','']:
            with self.assertRaisesRegex(ValueError,'TIERS'):expand_tiers(value)
