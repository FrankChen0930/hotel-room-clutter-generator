import unittest
from common_core.repair import classify_native,repair


class RepairTests(unittest.TestCase):
    def plan(self):return dict(targets=dict(count=2),budgets=dict(native_retries=1))
    def result(self):return dict(objects=[dict(request_id='guest/book/0',effective=dict(support_id='desk'))])

    def test_one_new_attempt_and_terminal_exhaustion(self):
        assessment=dict(failure_kind='SUPPORT_OR_PENETRATION',attempt_id='a000')
        decision=repair(self.plan(),self.result(),assessment,dict(native_retries_used=0))
        self.assertEqual(decision['action'],'NEW_ATTEMPT');self.assertEqual(decision['rng_stream'],'repair')
        self.assertEqual(decision['request_count'],2);self.assertEqual(decision['parent_attempt_id'],'a000')
        exhausted=repair(self.plan(),self.result(),assessment,dict(native_retries_used=1))
        self.assertEqual(exhausted['action'],'TERMINAL');self.assertEqual(exhausted['reason'],'NATIVE_BUDGET_EXHAUSTED')

    def test_runtime_identity_and_initial_pose_errors_do_not_resample(self):
        for kind in ['RUNTIME_INCOMPLETE','RUNTIME_ERROR','IDENTITY_OR_SCOPE_ERROR','INITIAL_POSE_MISMATCH']:
            decision=repair(self.plan(),self.result(),dict(failure_kind=kind,attempt_id='a000'),dict(native_retries_used=0))
            self.assertEqual(decision['action'],'TERMINAL')

    def test_unknown_or_interrupted_native_results_not_geometry(self):
        self.assertEqual(classify_native(None,dict(termination_reason='WATCHDOG_TIMEOUT')),'RUNTIME_INCOMPLETE')
        self.assertEqual(classify_native(dict(outcome='UNKNOWN'),{}),'RUNTIME_INCOMPLETE')

    def test_historical_or_incomplete_pass_is_not_promoted(self):
        report=dict(execution='EXECUTED',outcome='PASS',checks=dict(native_steps=False,native_120hz=True))
        self.assertEqual(classify_native(report,dict(native_exit_code=0)),'RUNTIME_INCOMPLETE')

    def test_recorded_pass_and_total_geometry_budget_not_promoted(self):
        self.assertEqual(classify_native(dict(execution='RECORDED',outcome='PASS'),dict(native_exit_code=0)),'RECORDED_OR_UNVERIFIED_RESULT')
        plan=self.plan();plan['budgets']['max_samples_per_request']=1;plan['requests']=[dict(request_id='guest/book/0')]
        result=self.result();result['sampling']=[dict(request_id='guest/book/0',samples=1)]
        decision=repair(plan,result,dict(failure_kind='UNSTABLE',attempt_id='a000'),dict(native_retries_used=0))
        self.assertEqual(decision['reason'],'GEOMETRY_BUDGET_EXHAUSTED')
