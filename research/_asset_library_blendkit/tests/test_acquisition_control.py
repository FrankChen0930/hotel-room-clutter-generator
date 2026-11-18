import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from acquisition_control import decision,validate_queries

class AcquisitionControlTests(unittest.TestCase):
    settings=dict(target_local_ready=125,max_total_sources=220,max_elapsed_s=21600,max_original_bytes=8*1024**3)
    def result(self,control=None,**changes):
        values=dict(acquired_count=43,local_ready=13,elapsed_s=10,original_bytes=1000);values.update(changes)
        return decision(self.settings,control or {},**values)
    def test_all_limits_are_terminal_even_when_paused(self):
        for args,expected in [(dict(local_ready=125),'LOCAL_TARGET_REACHED'),(dict(acquired_count=220),'SOURCE_POOL_LIMIT_REACHED'),(dict(elapsed_s=21600),'SESSION_TIME_LIMIT_REACHED'),(dict(original_bytes=8*1024**3),'SOURCE_BYTES_LIMIT_REACHED')]:
            self.assertEqual(self.result(dict(pause=True),**args),expected)
    def test_local_control_does_not_require_gui_per_batch(self):
        self.assertEqual(self.result(),'CONTINUE')
        self.assertEqual(self.result(dict(pause=True)),'PAUSED')
        self.assertEqual(self.result(dict(stop=True)),'STOP_REQUESTED')
    def test_data_queue_validation(self):
        valid=dict(query='toothbrush',category='toiletry',scenario='bathroom_use',regions=['cabinet'])
        self.assertEqual(validate_queries([valid]),[valid])
        for jobs in [[dict(valid,category='furniture')],[dict(valid,query='x'*81)],[valid]*401]:
            with self.assertRaises(ValueError):validate_queries(jobs)

if __name__=='__main__':unittest.main()
