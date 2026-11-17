import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from common_core.identity import sha256_file
from common_core.progress import append_event,event_from_receipt,summary


class ProgressTests(unittest.TestCase):
    def test_receipt_proof_dedup_failure_and_stale_evidence(self):
        actual=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir=actual/'_common_core_runs') as temporary:
            root=Path(temporary);runs=root/'_common_core_runs';planning=root/'_common_core_planning';runs.mkdir();planning.mkdir()
            log=runs/'log.txt';log.write_text('actual execution\n');gate=runs/'gates.json';gate.write_text(json.dumps(dict(execution='EXECUTED',outcome='PASS')))
            receipt=dict(event_id='fixture',unit_id='WU-19',status='COMPLETE',commands=[dict(evidence_ref='_common_core_runs/log.txt',sha256=sha256_file(log),exit_code=0)],evidence_refs=[],failure_reason=None)
            path=runs/'receipt.json';path.write_text(json.dumps(receipt));ledger=planning/'ledger.jsonl'
            with patch('common_core.progress.ROOT',root):
                with self.assertRaisesRegex(ValueError,'VERSION_REQUIRED'):event_from_receipt(path,'COMPLETE',gates=[gate])
                with self.assertRaisesRegex(ValueError,'GATES_REQUIRED'):event_from_receipt(path,'COMPLETE','a'*40)
                gate.write_text(json.dumps(dict(execution='RECORDED',outcome='PASS')))
                with self.assertRaisesRegex(ValueError,'GATE_FAILED'):event_from_receipt(path,'COMPLETE','a'*40,[gate])
                gate.write_text(json.dumps(dict(execution='EXECUTED',outcome='PASS')))
                event=event_from_receipt(path,'COMPLETE','a'*40,[gate]);self.assertTrue(append_event(ledger,event));self.assertFalse(append_event(ledger,event))
                self.assertIn('[receipt.json]',summary(ledger));self.assertEqual(len(ledger.read_text().splitlines()),1)
                with self.assertRaisesRegex(ValueError,'CONFLICT'):append_event(ledger,dict(event,code_commit='b'*40))
                receipt.update(status='FAILED',failure_reason='INTERRUPTED');receipt['commands'][0]['exit_code']=6;path.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError,'UNPROVEN'):event_from_receipt(path,'COMPLETE','a'*40,[gate])
                failed=event_from_receipt(path,'INCOMPLETE');self.assertEqual(failed['status'],'INCOMPLETE');self.assertEqual(failed['failure_reason'],'INTERRUPTED')
                with self.assertRaisesRegex(ValueError,'STALE_EVIDENCE'):summary(ledger)
                log.write_text('tampered')
                with self.assertRaisesRegex(ValueError,'LOG_HASH'):event_from_receipt(path,'INCOMPLETE')

    def test_outside_planning_path_rejected(self):
        from common_core.progress import checked_path
        with self.assertRaisesRegex(ValueError,'PATH_SCOPE'):checked_path('C:/outside-progress.json',Path(__file__).resolve().parents[2]/'_common_core_planning')
