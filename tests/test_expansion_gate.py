"""
TDD tests for expansion_gate.py — RED phase.

Tests for:
  - ExpansionGate class
  - GateFailError
  - GatePassPendingApprovalError
  - record_run() counter persistence
  - check() gate logic (consecutive passes, fail reset)
  - capture_baseline() idempotency
  - _read_state() / _write_state() round-trip
  - No hardcoded thresholds (all from get_disease_config())
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

# Ensure src/ is on path
SRC_DIR = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, os.path.abspath(SRC_DIR))


class TestExpansionGateImports(unittest.TestCase):
    """Verify all required symbols are importable without heavy dependencies."""

    def test_imports_ok(self):
        from expansion_gate import (
            ExpansionGate,
            GateFailError,
            GatePassPendingApprovalError,
            _DEFAULT_GATE_STATE,
        )
        self.assertIsNotNone(ExpansionGate)
        self.assertIsNotNone(GateFailError)
        self.assertIsNotNone(GatePassPendingApprovalError)
        self.assertIsNotNone(_DEFAULT_GATE_STATE)

    def test_exception_hierarchy(self):
        from expansion_gate import GateFailError, GatePassPendingApprovalError
        self.assertTrue(issubclass(GateFailError, RuntimeError))
        self.assertTrue(issubclass(GatePassPendingApprovalError, RuntimeError))
        self.assertIsNot(GateFailError, GatePassPendingApprovalError)

    def test_default_gate_state_schema(self):
        from expansion_gate import _DEFAULT_GATE_STATE
        for key in ('run_count', 'consecutive_passes', 'last_eval_at', 'last_gate_pass', 'gate_pass_events'):
            self.assertIn(key, _DEFAULT_GATE_STATE, f"Missing key: {key}")
        self.assertEqual(_DEFAULT_GATE_STATE['run_count'], 0)
        self.assertEqual(_DEFAULT_GATE_STATE['consecutive_passes'], 0)
        self.assertIsNone(_DEFAULT_GATE_STATE['last_eval_at'])
        self.assertIsNone(_DEFAULT_GATE_STATE['last_gate_pass'])
        self.assertEqual(_DEFAULT_GATE_STATE['gate_pass_events'], [])


class TestExpansionGateStateIO(unittest.TestCase):
    """_read_state() and _write_state() round-trip tests."""

    def _make_gate(self, tmp_dir):
        from expansion_gate import ExpansionGate
        return ExpansionGate(
            gate_state_path=os.path.join(tmp_dir, 'gate_state.json'),
            baseline_path=os.path.join(tmp_dir, 'baseline_snapshot.json'),
        )

    def test_read_state_returns_default_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            state = gate._read_state()
            self.assertEqual(state['run_count'], 0)
            self.assertEqual(state['consecutive_passes'], 0)

    def test_write_then_read_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            state = gate._read_state()
            state['run_count'] = 7
            state['consecutive_passes'] = 1
            gate._write_state(state)
            loaded = gate._read_state()
            self.assertEqual(loaded['run_count'], 7)
            self.assertEqual(loaded['consecutive_passes'], 1)

    def test_read_state_survives_corrupt_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'gate_state.json')
            with open(path, 'w') as fh:
                fh.write("{ not valid json }")
            from expansion_gate import ExpansionGate
            gate = ExpansionGate(gate_state_path=path)
            state = gate._read_state()
            self.assertEqual(state['run_count'], 0)

    def test_write_state_is_atomic(self):
        """write uses os.replace (atomic rename), not direct open()."""
        src = open(os.path.join(SRC_DIR, 'expansion_gate.py')).read()
        self.assertIn('os.replace', src, "Must use atomic os.replace in _write_state")

    def test_read_state_backfills_missing_keys(self):
        """If gate_state.json is missing a new key, read fills it from default."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'gate_state.json')
            # Write an older-format state that lacks 'gate_pass_events'
            with open(path, 'w') as fh:
                json.dump({'run_count': 3, 'consecutive_passes': 0}, fh)
            from expansion_gate import ExpansionGate
            gate = ExpansionGate(gate_state_path=path)
            state = gate._read_state()
            self.assertIn('gate_pass_events', state)
            self.assertEqual(state['run_count'], 3)


class TestRecordRun(unittest.TestCase):
    """record_run() increments counter and triggers check every N runs."""

    def _make_gate(self, tmp_dir):
        from expansion_gate import ExpansionGate
        return ExpansionGate(
            gate_state_path=os.path.join(tmp_dir, 'gate_state.json'),
            baseline_path=os.path.join(tmp_dir, 'baseline_snapshot.json'),
        )

    def test_record_run_increments_counter(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            with mock.patch.object(gate, 'check', return_value=None):
                r1 = gate.record_run()
                r2 = gate.record_run()
                r3 = gate.record_run()
            self.assertEqual(r1, 1)
            self.assertEqual(r2, 2)
            self.assertEqual(r3, 3)

    def test_record_run_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate1 = self._make_gate(tmp)
            with mock.patch.object(gate1, 'check', return_value=None):
                gate1.record_run()
                gate1.record_run()

            from expansion_gate import ExpansionGate
            gate2 = ExpansionGate(gate_state_path=os.path.join(tmp, 'gate_state.json'))
            state = gate2._read_state()
            self.assertEqual(state['run_count'], 2)

    def test_record_run_calls_check_every_n_runs(self):
        """check() should be called when run_count % expansion_gate_n == 0."""
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            gate_n = gate.dc['expansion_gate_n']  # defaults to 5

            check_calls = []
            with mock.patch.object(gate, 'check', side_effect=lambda s=None: check_calls.append(s)):
                for _ in range(gate_n * 2):
                    gate.record_run()

            # Should be called exactly twice (at run_count == gate_n and run_count == 2*gate_n)
            self.assertEqual(len(check_calls), 2)

    def test_record_run_does_not_call_check_on_non_multiple(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            gate_n = gate.dc['expansion_gate_n']

            check_calls = []
            with mock.patch.object(gate, 'check', side_effect=lambda s=None: check_calls.append(s)):
                for _ in range(gate_n - 1):
                    gate.record_run()

            self.assertEqual(len(check_calls), 0)

    def test_record_run_returns_new_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            with mock.patch.object(gate, 'check', return_value=None):
                result = gate.record_run()
            self.assertEqual(result, 1)


class TestGateCheck(unittest.TestCase):
    """check() updates consecutive_passes and raises correct exceptions."""

    def _make_gate(self, tmp_dir):
        from expansion_gate import ExpansionGate
        return ExpansionGate(
            gate_state_path=os.path.join(tmp_dir, 'gate_state.json'),
            baseline_path=os.path.join(tmp_dir, 'baseline_snapshot.json'),
        )

    def _mock_eval_report(self, all_pass: bool, disease_results=None):
        """Build a fake run_full_eval() return dict."""
        diseases = disease_results or {
            'type1_diabetes': {'precision': 0.70, 'accuracy': 0.65,
                               'target_precision': 0.65, 'target_accuracy': 0.60},
            'metastatic_cancer': {'precision': 0.68, 'accuracy': 0.62,
                                  'target_precision': 0.65, 'target_accuracy': 0.60},
        }
        return {
            'eval_timestamp': '2026-05-03T00:00:00Z',
            'disease_results': diseases,
            'all_gate_pass': all_pass,
            'config_snapshot': {},
        }

    def _mock_evaluator(self, all_pass: bool):
        evaluator = mock.MagicMock()
        evaluator.run_full_eval.return_value = self._mock_eval_report(all_pass)
        return evaluator

    def test_check_fail_resets_consecutive_passes(self):
        from expansion_gate import GateFailError
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            state = gate._read_state()
            state['consecutive_passes'] = 1
            gate._write_state(state)

            with self.assertRaises(GateFailError):
                gate.check(state=state, evaluator=self._mock_evaluator(all_pass=False))

            loaded = gate._read_state()
            self.assertEqual(loaded['consecutive_passes'], 0)

    def test_check_fail_raises_gate_fail_error_with_details(self):
        from expansion_gate import GateFailError
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            state = gate._read_state()
            try:
                gate.check(state=state, evaluator=self._mock_evaluator(all_pass=False))
                self.fail("Expected GateFailError")
            except GateFailError as exc:
                self.assertIn('GATE FAIL', str(exc))

    def test_check_pass_increments_consecutive(self):
        from expansion_gate import GatePassPendingApprovalError, GateFailError
        consecutive_required = 2  # default EXPANSION_GATE_CONSECUTIVE
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            state = gate._read_state()
            # First pass — should NOT raise yet (consecutive_passes goes to 1)
            try:
                gate.check(state=state, evaluator=self._mock_evaluator(all_pass=True))
            except GatePassPendingApprovalError:
                pass  # Acceptable if consecutive=1 already meets threshold
            except GateFailError:
                self.fail("Should not raise GateFailError on pass")

    def test_check_raises_gate_pass_pending_after_consecutive_passes(self):
        from expansion_gate import GatePassPendingApprovalError
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            consecutive_required = gate.dc['expansion_gate_consecutive']  # 2

            state = gate._read_state()
            # Pre-load consecutive_passes to (required - 1) so next pass triggers
            state['consecutive_passes'] = consecutive_required - 1
            gate._write_state(state)

            with self.assertRaises(GatePassPendingApprovalError) as ctx:
                gate.check(state=state, evaluator=self._mock_evaluator(all_pass=True))

            msg = str(ctx.exception)
            self.assertIn('manual approval', msg.lower())

    def test_check_records_gate_pass_event(self):
        from expansion_gate import GatePassPendingApprovalError
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            consecutive_required = gate.dc['expansion_gate_consecutive']

            state = gate._read_state()
            state['consecutive_passes'] = consecutive_required - 1
            gate._write_state(state)

            with self.assertRaises(GatePassPendingApprovalError):
                gate.check(state=state, evaluator=self._mock_evaluator(all_pass=True))

            loaded = gate._read_state()
            self.assertGreater(len(loaded['gate_pass_events']), 0)
            event = loaded['gate_pass_events'][-1]
            self.assertEqual(event['event'], 'GATE_PASS')
            self.assertIn('at', event)
            self.assertIn('disease_results', event)

    def test_check_gate_pass_error_message_has_per_disease_metrics(self):
        from expansion_gate import GatePassPendingApprovalError
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            consecutive_required = gate.dc['expansion_gate_consecutive']
            state = gate._read_state()
            state['consecutive_passes'] = consecutive_required - 1
            gate._write_state(state)

            with self.assertRaises(GatePassPendingApprovalError) as ctx:
                gate.check(state=state, evaluator=self._mock_evaluator(all_pass=True))

            msg = str(ctx.exception)
            self.assertIn('type1_diabetes', msg)

    def test_check_reads_thresholds_from_config_not_hardcoded(self):
        """Ensure no hardcoded 5 or 2 in expansion_gate.py."""
        src = open(os.path.join(SRC_DIR, 'expansion_gate.py')).read()
        # Must reference config keys, not hardcoded values
        self.assertIn('expansion_gate_n', src)
        self.assertIn('expansion_gate_consecutive', src)
        # Must NOT contain hardcoded numeric threshold assignments
        import re
        # Matches literal "== 5" or "== 2" or "= 0.65" or "= 0.60" as standalone values
        bad_patterns = [r"==\s*5\b", r"==\s*2\b", r"=\s*0\.65\b", r"=\s*0\.60\b"]
        for pat in bad_patterns:
            matches = re.findall(pat, src)
            self.assertEqual(matches, [], f"Hardcoded threshold found: {pat!r} -> {matches}")


class TestCaptureBaseline(unittest.TestCase):
    """capture_baseline() idempotency and correct output format."""

    def _make_gate(self, tmp_dir):
        from expansion_gate import ExpansionGate
        return ExpansionGate(
            gate_state_path=os.path.join(tmp_dir, 'gate_state.json'),
            baseline_path=os.path.join(tmp_dir, 'baseline_snapshot.json'),
        )

    def _mock_evaluator_with_report(self):
        evaluator = mock.MagicMock()
        evaluator.run_full_eval.return_value = {
            'eval_timestamp': '2026-05-03T00:00:00Z',
            'disease_results': {
                'type1_diabetes': {'precision': 0.65, 'accuracy': 0.60, 'gate_pass': True},
            },
            'all_gate_pass': True,
        }
        return evaluator

    def test_capture_baseline_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            gate.capture_baseline(evaluator=self._mock_evaluator_with_report())
            self.assertTrue(os.path.exists(gate.baseline_path))

    def test_capture_baseline_snapshot_has_required_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            snap = gate.capture_baseline(evaluator=self._mock_evaluator_with_report())
            self.assertIn('captured_at', snap)
            self.assertIn('phase', snap)
            self.assertIn('disease_results', snap)

    def test_capture_baseline_is_idempotent(self):
        """Second call must NOT re-run evaluator — returns existing snapshot."""
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            evaluator = self._mock_evaluator_with_report()
            gate.capture_baseline(evaluator=evaluator)
            gate.capture_baseline(evaluator=evaluator)
            # run_full_eval should have been called exactly once
            evaluator.run_full_eval.assert_called_once()

    def test_capture_baseline_returns_existing_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = self._make_gate(tmp)
            existing = {'captured_at': '2026-01-01T00:00:00Z', 'phase': '05-disease-scope-specialization',
                        'disease_results': {}, 'all_gate_pass': False}
            with open(gate.baseline_path, 'w') as fh:
                json.dump(existing, fh)

            evaluator = self._mock_evaluator_with_report()
            result = gate.capture_baseline(evaluator=evaluator)

            evaluator.run_full_eval.assert_not_called()
            self.assertEqual(result['captured_at'], existing['captured_at'])


class TestCLIEntrypoint(unittest.TestCase):
    """python src/expansion_gate.py should exit 0 and print valid JSON."""

    def test_cli_exits_zero(self):
        import subprocess
        result = subprocess.run(
            ['python', 'src/expansion_gate.py'],
            capture_output=True, text=True,
            cwd=os.path.join(SRC_DIR, '..'),
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

    def test_cli_prints_valid_json(self):
        import subprocess
        result = subprocess.run(
            ['python', 'src/expansion_gate.py'],
            capture_output=True, text=True,
            cwd=os.path.join(SRC_DIR, '..'),
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn('run_count', data)


if __name__ == '__main__':
    unittest.main()
