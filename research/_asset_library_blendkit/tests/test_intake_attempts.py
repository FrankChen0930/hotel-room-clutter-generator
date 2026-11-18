from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from intake_attempts import reserve_attempt

class ReopenTests(unittest.TestCase):
    def test_reopen_preserves_old_attempt_and_allocates_next(self):
        with tempfile.TemporaryDirectory() as folder:
            first=reserve_attempt(folder)
            evidence=first/'session.json';evidence.write_bytes(b'original evidence')
            second=reserve_attempt(folder);third=reserve_attempt(folder)
            self.assertEqual([first.name,second.name,third.name],['intake_user_001','intake_user_002','intake_user_003'])
            self.assertEqual(evidence.read_bytes(),b'original evidence')
    def test_existing_file_does_not_get_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'intake_user_001').write_bytes(b'keep')
            self.assertEqual(reserve_attempt(folder).name,'intake_user_002')
            self.assertEqual((Path(folder)/'intake_user_001').read_bytes(),b'keep')
    def test_rejects_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('../escape','a/b','a\\b','C:bad',''):
                with self.assertRaises(ValueError):reserve_attempt(folder,name)

if __name__=='__main__':unittest.main()
