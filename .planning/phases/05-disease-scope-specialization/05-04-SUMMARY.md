---
phase: "05"
plan: "04"
subsystem: expansion-gate
tags: [expansion-gate, disease-scope, phase5, D-06, FOCUS-01, FOCUS-03]
dependency_graph:
  requires:
    - "05-01"   # DiseaseKBBuckets and get_disease_config()
    - "05-03"   # DiseaseEvaluator.run_full_eval() interface
  provides:
    - expansion-gate-counter    # persistent run counter in data/gate_state.json
    - gate-fail-error           # GateFailError exception class
    - gate-pass-error           # GatePassPendingApprovalError exception class
    - baseline-snapshot         # data/baseline_snapshot.json (captured once)
    - medical-verifier-wiring   # record_run() integrated into verify_multiple_summaries()
  affects:
    - src/medical_verifier.py   # verify_multiple_summaries() now calls record_run()
tech_stack:
  added: []
  patterns:
    - atomic-file-write (os.replace for gate_state.json)
    - lazy-import (DiseaseEvaluator imported inside check() to avoid circular deps)
    - idempotent-baseline (capture_baseline() skips re-eval if file exists)
key_files:
  created:
    - src/expansion_gate.py
    - tests/test_expansion_gate.py
  modified:
    - src/medical_verifier.py
decisions:
  - "D-06 gate is human-in-the-loop: GatePassPendingApprovalError raises on consecutive pass, no auto-expansion"
  - "DiseaseEvaluator is lazy-imported inside check() to avoid heavy model load at module import time"
  - "capture_baseline() is fully idempotent: returns existing file without re-running eval"
  - "record_run() uses non-blocking try/except in verify_multiple_summaries() so gate state errors never abort verification — only GateFailError/GatePassPendingApprovalError propagate to caller"
  - "os.replace() used for atomic gate_state.json writes to prevent partial writes"
metrics:
  duration: "4 minutes"
  completed: "2026-05-03"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 05 Plan 04: Expansion Gate and MedicalVerifier Wiring Summary

**One-liner:** Persistent run-counter gate using JSON state and DiseaseEvaluator.run_full_eval() to enforce 2-consecutive-pass human-approval requirement before multi-disease expansion (D-06).

## What Was Built

### Task 1: src/expansion_gate.py

Created the expansion gate module implementing D-06 requirements:

**Classes:**
- `GateFailError(RuntimeError)` — raised when gate check fails (metrics below target)
- `GatePassPendingApprovalError(RuntimeError)` — raised when consecutive passes >= `EXPANSION_GATE_CONSECUTIVE`; requires human approval
- `ExpansionGate` — orchestrates state persistence and gate evaluation

**Key methods:**
- `_read_state()` — loads `data/gate_state.json`; returns default state if missing/corrupt; backfills missing keys for forward compatibility
- `_write_state(state)` — atomic write via `os.replace()` to prevent partial writes
- `record_run()` — increments `run_count`; triggers `check()` when `run_count % expansion_gate_n == 0`; returns new count
- `check(state, evaluator, verifier)` — calls `DiseaseEvaluator.run_full_eval()`; updates `consecutive_passes`; raises `GatePassPendingApprovalError` when streak meets threshold or `GateFailError` on metric failure
- `capture_baseline(evaluator, verifier)` — runs eval once, writes to `data/baseline_snapshot.json`; skips if file already exists (idempotent)

**gate_state.json schema:**
```json
{
  "run_count": 0,
  "consecutive_passes": 0,
  "last_eval_at": null,
  "last_gate_pass": null,
  "gate_pass_events": []
}
```

**No hardcoded thresholds** — all gate parameters read from `get_disease_config()`:
- `expansion_gate_n` (default: 5) — evaluate every N runs
- `expansion_gate_consecutive` (default: 2) — consecutive passes required
- `precision_target` (0.65), `accuracy_target` (0.60) — evaluated inside DiseaseEvaluator

### Task 2: MedicalVerifier wiring

Added to `verify_multiple_summaries()` after `all_results` is populated:

```python
# Phase 5 D-06: record this pipeline run in the expansion gate counter
try:
    from expansion_gate import ExpansionGate, GateFailError, GatePassPendingApprovalError
    ExpansionGate().record_run()
except (GateFailError, GatePassPendingApprovalError):
    raise  # Propagate gate signals to caller
except Exception:
    pass   # Non-blocking — gate state errors must not abort verification
```

**Integration point:** Line ~140 in `src/medical_verifier.py`, end of `verify_multiple_summaries()`.

**Baseline snapshot location:** `data/baseline_snapshot.json` (auto-created on first `capture_baseline()` call; never overwritten).

**Human approval requirement:** The gate is strictly human-in-the-loop per D-06. `GatePassPendingApprovalError` surfaces to the operator; no code path exists that triggers automatic expansion.

## TDD Gate Compliance

- RED commit: `ad2ccbe` — `test(05-04): add failing tests for expansion_gate.py (RED phase)`
- GREEN commit: `2b58348` — `feat(05-04): implement expansion_gate.py with ExpansionGate, GateFailError, GatePassPendingApprovalError`
- 26 expansion gate tests pass; 163 pre-existing tests unaffected

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all gate logic is fully implemented with no placeholder data.

## Pre-existing Test Failure (out of scope)

`tests/test_safety_guards.py::test_input_validation_rejects_non_string` was already failing before this plan (confirmed via `git stash` check). Not caused by Plan 04 changes. Deferred to separate fix.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond the planned `gate_state.json` and `baseline_snapshot.json` files already documented in the threat model (T-05-12 through T-05-15).

## Self-Check: PASSED

- `src/expansion_gate.py` — FOUND
- `tests/test_expansion_gate.py` — FOUND
- `src/medical_verifier.py` wiring — FOUND (grep confirmed lines 142-143)
- Commit `ad2ccbe` (RED) — FOUND
- Commit `2b58348` (GREEN) — FOUND
- Commit `a40b6bb` (verifier wiring) — FOUND
- `python src/expansion_gate.py` exits 0 — CONFIRMED
- All 163 non-pre-existing tests pass — CONFIRMED
