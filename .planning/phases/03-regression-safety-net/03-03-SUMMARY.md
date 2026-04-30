---
phase: 03-regression-safety-net
plan: "03"
subsystem: tests
tags: [regression, confidence-scoring, mocking, TEST-03]
dependency_graph:
  requires:
    - src/claim_extractor_fixed.py::calculate_confidence_score
    - src/medical_config.py::get_global_config
  provides:
    - tests/test_confidence_scoring.py::TestConfidenceScoring
  affects: []
tech_stack:
  added: []
  patterns:
    - ClaimExtractor.__new__ shell injection
    - mock.patch.object on module-level import to resolve conftest session mock
    - numpy-based cosine_similarity replacement returning shape (1,1) ndarray
key_files:
  created:
    - tests/test_confidence_scoring.py
  modified: []
decisions:
  - "Used mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim) to resolve conftest session-wide sklearn MagicMock (D-08 pattern)"
  - "Asserted label == 'HIGH' for identical embeddings + grade-A facts (composite score ~0.92 >> HIGH threshold 0.30) — no threshold relaxation needed"
  - "Asserted isinstance(score, float) as fast MagicMock-leak detector per D-12"
  - "No exact float assertions on score; only label membership and [0.0, 1.0] range"
metrics:
  duration: "5 minutes"
  completed: "2026-04-30"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 03 Plan 03: Confidence Score Regression Tests Summary

New test file `tests/test_confidence_scoring.py` implementing TEST-03 — regression coverage for `ClaimExtractor.calculate_confidence_score()` label/score contract, with local numpy-based cosine_similarity mock to neutralize the conftest session-wide sklearn MagicMock.

## What Was Built

**`tests/test_confidence_scoring.py`** — `class TestConfidenceScoring` with 4 tests:

| Test | Fixture / Regime | Assertion |
|------|-----------------|-----------|
| `test_high_similarity_facts_yield_high_label` | Identical embeddings + grade-A, quality=0.9 | `label == 'HIGH'`, `isinstance(score, float)`, `0.0 <= score <= 1.0` |
| `test_absent_supporting_facts_yield_low_label` | Empty supporting_facts list | `label == 'LOW'` (early-return path) |
| `test_orthogonal_facts_yield_low_or_medium` | Gram-Schmidt orthogonal vectors + grade-D | `label != 'HIGH'` |
| `test_score_and_label_bounds_always_valid` | Mixed grade-B/C facts | `label in ('HIGH','MEDIUM','LOW')`, `0.0 <= score <= 1.0` |

## Cosine Mock Resolution (D-08)

`conftest.py` registers `sklearn.metrics.pairwise` as a `MagicMock` at session scope before any module import. `claim_extractor_fixed.py` binds `cosine_similarity` at module load from that mock, so `claim_extractor_fixed.cosine_similarity` is a `MagicMock` whose return is also a `MagicMock` (non-numeric).

Resolution applied: each test uses `mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim)` in a `with` block. The `_np_cosine_sim` helper:

```python
def _np_cosine_sim(a, b):
    a_flat = np.asarray(a).flatten()
    b_flat = np.asarray(b).flatten()
    denom = np.linalg.norm(a_flat) * np.linalg.norm(b_flat)
    val = float(np.dot(a_flat, b_flat) / denom) if denom > 0 else 0.0
    return np.array([[val]])   # shape (1,1) matches sklearn contract
```

The `with` block scope ensures the patch is automatically removed after each test, preventing cross-test mock bleed (T-03-10).

## Threshold Analysis (HIGH test)

With `cosine_sim = 1.0` (identical embeddings), `quality_score = 0.9`, `evidence_grade = 'A'`, `distance = 0.1`:

- `base_similarity_score ≈ 0.80` (weights: avg=0.40, max=0.20, dist=0.20)
- `preprocessed_quality = 0.9 * 1.0 * 1.0 = 0.9`
- `composite_score ≈ 0.80 * 0.9 + 1.0 * 0.20 = 0.92`
- `CONFIDENCE_HIGH = 0.30` → composite 0.92 >> 0.30 → label = 'HIGH'

No threshold relaxation was needed. The assertion `label == 'HIGH'` holds reliably.

## MagicMock Leak Guard (D-12)

Each test asserts `isinstance(score, float)`. If the cosine patch were to fail silently, arithmetic on a `MagicMock` would produce another `MagicMock`, not a `float`, and this assertion would fail immediately with a clear diagnostic.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

### Files created
- `tests/test_confidence_scoring.py` — FOUND

### Commits
- `cb31968` — FOUND

## Self-Check: PASSED

## Threat Surface Scan

No new production code modified; no new network endpoints, auth paths, or schema changes introduced. Test-only file. No threat flags.
