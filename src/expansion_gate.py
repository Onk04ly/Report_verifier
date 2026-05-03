"""
Expansion Gate for Phase 5 Disease Scope Specialization.

Implements D-06: auto-evaluate gate every EXPANSION_GATE_N pipeline runs;
require EXPANSION_GATE_CONSECUTIVE consecutive passing runs before flagging
for manual approval of broad multi-disease expansion.

No automatic expansion occurs. Human approval is always required on gate pass.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

from medical_config import get_global_config


class GateFailError(RuntimeError):
    """Raised when the expansion gate check fails (metrics below target).

    Pipeline should pause and surface this to the operator for review.
    """


class GatePassPendingApprovalError(RuntimeError):
    """Raised when the expansion gate passes N consecutive runs.

    No automatic expansion occurs. The operator must manually approve
    multi-disease expansion before the pipeline can proceed.
    """


_DEFAULT_GATE_STATE: Dict[str, Any] = {
    'run_count': 0,
    'consecutive_passes': 0,
    'last_eval_at': None,
    'last_gate_pass': None,
    'gate_pass_events': [],
}


class ExpansionGate:
    """Persistent gate that auto-evaluates disease metrics every N pipeline runs.

    State is persisted to gate_state_path (default: data/gate_state.json) so
    the run counter survives process restarts.

    Usage:
        gate = ExpansionGate()
        gate.record_run()    # call once per verify_multiple_summaries() invocation
    """

    def __init__(self, gate_state_path=None, baseline_path=None, config=None):
        self.cfg = config or get_global_config()
        self.dc = self.cfg.get_disease_config()
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        self.gate_state_path = gate_state_path or os.path.normpath(
            os.path.join(base, 'data', 'gate_state.json')
        )
        self.baseline_path = baseline_path or os.path.normpath(
            os.path.join(base, 'data', 'baseline_snapshot.json')
        )

    def _read_state(self) -> Dict[str, Any]:
        """Load gate_state.json or return default state if missing/corrupt."""
        if not os.path.exists(self.gate_state_path):
            return dict(_DEFAULT_GATE_STATE)
        try:
            with open(self.gate_state_path, 'r', encoding='utf-8') as fh:
                state = json.load(fh)
            # Ensure all expected keys exist (forward compatibility)
            for k, v in _DEFAULT_GATE_STATE.items():
                if k not in state:
                    state[k] = v if not isinstance(v, list) else list(v)
            return state
        except Exception:
            return dict(_DEFAULT_GATE_STATE)

    def _write_state(self, state: Dict[str, Any]) -> None:
        """Persist gate state to disk atomically (write then rename)."""
        os.makedirs(os.path.dirname(os.path.abspath(self.gate_state_path)), exist_ok=True)
        tmp_path = self.gate_state_path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(state, fh, indent=2)
        os.replace(tmp_path, self.gate_state_path)

    def record_run(self) -> int:
        """Increment the run counter and persist. Returns the new run count.

        Call once per verify_multiple_summaries() invocation.
        After incrementing, if run_count % expansion_gate_n == 0: call check().
        """
        state = self._read_state()
        state['run_count'] += 1
        self._write_state(state)
        run_count = state['run_count']

        gate_n = self.dc['expansion_gate_n']
        if run_count % gate_n == 0:
            print(
                f"[ExpansionGate] Run {run_count}: auto-evaluating gate "
                f"(every {gate_n} runs)..."
            )
            self.check(state)

        return run_count

    def check(
        self,
        state: Optional[Dict[str, Any]] = None,
        evaluator=None,
        verifier=None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate all diseases and update consecutive-pass streak.

        Raises:
            GatePassPendingApprovalError: if consecutive passes >= EXPANSION_GATE_CONSECUTIVE
            GateFailError: if any disease fails to meet targets
        Returns:
            The evaluation report dict if evaluation ran; None if skipped.
        """
        from disease_evaluator import DiseaseEvaluator  # noqa: PLC0415

        if state is None:
            state = self._read_state()

        if evaluator is None:
            evaluator = DiseaseEvaluator(config=self.cfg)

        report = evaluator.run_full_eval(verifier=verifier)
        state['last_eval_at'] = datetime.utcnow().isoformat() + 'Z'
        all_pass = report.get('all_gate_pass', False)
        state['last_gate_pass'] = all_pass

        if all_pass:
            state['consecutive_passes'] += 1
            consecutive_required = self.dc['expansion_gate_consecutive']
            print(
                f"[ExpansionGate] Gate PASSED — consecutive passes: "
                f"{state['consecutive_passes']}/{consecutive_required}"
            )
            if state['consecutive_passes'] >= consecutive_required:
                event = {
                    'event': 'GATE_PASS',
                    'at': state['last_eval_at'],
                    'run_count': state['run_count'],
                    'disease_results': {
                        d: {
                            'precision': r.get('precision'),
                            'accuracy': r.get('accuracy'),
                        }
                        for d, r in report.get('disease_results', {}).items()
                    },
                }
                state['gate_pass_events'].append(event)
                self._write_state(state)
                msg = (
                    f"GATE PASS — {state['consecutive_passes']} consecutive passing runs "
                    f"achieved. Manual approval required before multi-disease expansion. "
                    f"Metrics: {event['disease_results']}"
                )
                print(f"[ExpansionGate] {msg}")
                raise GatePassPendingApprovalError(msg)
        else:
            state['consecutive_passes'] = 0
            disease_summary = {
                d: {
                    'precision': r.get('precision'),
                    'accuracy': r.get('accuracy'),
                    'target_precision': r.get('target_precision'),
                    'target_accuracy': r.get('target_accuracy'),
                }
                for d, r in report.get('disease_results', {}).items()
            }
            fail_msg = (
                f"GATE FAIL ALERT: per-disease metrics below target. "
                f"Details: {disease_summary}"
            )
            print(f"[ExpansionGate] {fail_msg}")
            self._write_state(state)
            raise GateFailError(fail_msg)

        self._write_state(state)
        return report

    def capture_baseline(self, evaluator=None, verifier=None) -> Dict[str, Any]:
        """Capture the Phase 5 start baseline snapshot (run once only).

        If data/baseline_snapshot.json already exists, returns the existing
        snapshot without re-running the evaluation (D-02: baseline preserved
        once captured).
        """
        if os.path.exists(self.baseline_path):
            print(
                f"[ExpansionGate] Baseline already captured at "
                f"{self.baseline_path} — skipping."
            )
            with open(self.baseline_path, 'r', encoding='utf-8') as fh:
                return json.load(fh)

        from disease_evaluator import DiseaseEvaluator  # noqa: PLC0415

        if evaluator is None:
            evaluator = DiseaseEvaluator(config=self.cfg)

        print("[ExpansionGate] Capturing Phase 5 start baseline...")
        report = evaluator.run_full_eval(verifier=verifier)
        snapshot = {
            'captured_at': datetime.utcnow().isoformat() + 'Z',
            'phase': '05-disease-scope-specialization',
            'description': 'Broad model baseline at Phase 5 start (D-02)',
            'disease_results': report.get('disease_results', {}),
            'all_gate_pass': report.get('all_gate_pass', False),
        }

        os.makedirs(
            os.path.dirname(os.path.abspath(self.baseline_path)),
            exist_ok=True,
        )
        with open(self.baseline_path, 'w', encoding='utf-8') as fh:
            json.dump(snapshot, fh, indent=2)
        print(f"[ExpansionGate] Baseline saved to {self.baseline_path}")
        return snapshot


if __name__ == "__main__":
    # CLI: show current gate state
    gate = ExpansionGate()
    state = gate._read_state()
    print(json.dumps(state, indent=2))
