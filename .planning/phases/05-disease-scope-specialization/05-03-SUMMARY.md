---
phase: 05-disease-scope-specialization
plan: "03"
subsystem: disease-evaluator
tags: [disease-splits, evaluation, holdout, stratified-split, phase5, FOCUS-03]
dependency_graph:
  requires: [disease-config-block, disease-kb-buckets, disease-filtered-retrieval, disease-layer1-patterns]
  provides: [disease-dataset-splits, disease-eval-report, disease-gate-check]
  affects: [src/disease_evaluator.py, data/disease_splits.json, outputs/disease_eval_report.json]
tech_stack:
  added: []
  patterns: [stratified-tertile-split, numpy-rng-shuffle, lazy-load-pattern, json-persistence]
key_files:
  created:
    - src/disease_evaluator.py
    - data/disease_splits.json
  modified: []
decisions:
  - "Tertile percentile binning used for confidence tier stratification (top-33% high, mid-33% medium, bottom-34% low) to avoid empty tiers on KB quality_score range 0.30-0.775"
  - "evaluate_disease() uses verify_for_disease() (D-04 hybrid) NOT verify_single_summary() — both retrieval filtering and Layer 1 disease rules fire together"
  - "All precision/accuracy targets read from dc dict (precision_target, accuracy_target); no hardcoded thresholds"
  - "random_seed read from dc['random_seed'] — maps to DISEASE_RANDOM_SEED=42 in ConfigurationSettings"
  - "CLI entrypoint uses git-worktree-aware path resolution (same pattern as disease_buckets.py)"
  - "Pre-existing test failure test_risk_assessment::test_known_bad_hallucination_via_pipeline_not_low_risk (KeyError: stats) is out of scope — unrelated to this plan"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-03T09:22:00Z"
  tasks_completed: 1
  files_changed: 0
  files_created: 1
---

# Phase 05 Plan 03: Disease Evaluator Summary

## One-liner

Deterministic tertile-stratified KB splits (20/60/20) per disease and DiseaseEvaluator using verify_for_disease() (D-04 hybrid) to benchmark precision + accuracy on known-good holdout articles, writing an auditable eval report with config snapshot.

## What Was Built

### Task 1: DiseaseEvaluator with per-disease dataset splits

Created `src/disease_evaluator.py` as a self-contained evaluation module. Key components:

**DiseaseSplits dataclass:**
- Fields: train, tune, holdout (Dict[str, List[int]]), random_seed (int), built_at (ISO 8601)

**build_disease_splits(buckets, kb_csv_path, config):**
- Reads quality_score column from KB CSV (usecols for efficiency)
- Creates np.random.default_rng(dc['random_seed']) — fully reproducible
- Per disease: tertile percentile binning (p33=33.33, p67=66.67) to produce high/medium/low tiers
- Stratified shuffle-split per tier: n_holdout = ceil(n * 0.20), n_tune = ceil(n * 0.20), n_train = remainder
- Handles tiny buckets (2-3 articles) by reducing tune before holdout to keep n_train >= 0
- Concatenates tiers and sorts for deterministic ordering

**save_splits() / load_splits():**
- JSON serialisation with indent=2; lists preserved as plain arrays
- load_splits() raises FileNotFoundError with descriptive message

**DiseaseEvaluator class:**
- `__init__` resolves all 4 default paths relative to repo root; falls back via git-worktree pattern
- `ensure_buckets()` — loads disease_centroids.npz if present, else builds from scratch
- `ensure_splits()` — loads disease_splits.json if present, else builds and saves
- `evaluate_disease(disease, verifier)`:
  - Calls `verifier.verify_for_disease(text, disease, buckets)` (D-04 hybrid path)
  - Ground truth = all holdout articles are verified medical content
  - precision = accuracy = not_flagged / total (all-negative proxy evaluation)
  - Returns dict with flagged/not_flagged counts, precision, accuracy, gate_pass
- `run_full_eval(verifier, output_path)` — iterates disease_list, writes JSON report
- `check_gate_pass(report)` — returns bool from report['all_gate_pass']

## Split Sizes Per Disease

| Disease | Holdout | Train | Tune | Total |
|---------|---------|-------|------|-------|
| type1_diabetes | 810 | 2,422 | 810 | 4,042 |
| metastatic_cancer | 4,140 | 12,409 | 4,140 | 20,689 |

Holdout fraction: T1D = 810/4042 = 20.04%, MC = 4140/20689 = 20.01% (both within 15-25% tolerance)

## Split Strategy

- Stratification: tertile binning of quality_score within each disease bucket
- Tiers: top-33% = 'high', mid-33% = 'medium', bottom-34% = 'low'
- Per-tier shuffle with np.random.default_rng(42)
- Fractions: holdout=ceil(n*0.20), tune=ceil(n*0.20), train=n-holdout-tune
- No index overlap between train/tune/holdout verified and asserted

## Files Created

- `src/disease_evaluator.py` — 485 lines, all classes and functions per plan spec
- `data/disease_splits.json` — JSON with train/tune/holdout arrays + random_seed + built_at

## Eval Report Structure (outputs/disease_eval_report.json)

Written by run_full_eval() on each evaluation run:
```json
{
  "eval_timestamp": "2026-...",
  "disease_results": {
    "type1_diabetes": {
      "disease": "type1_diabetes",
      "total_holdout": 810,
      "flagged_count": N,
      "not_flagged_count": M,
      "precision": 0.XXXX,
      "accuracy": 0.XXXX,
      "target_precision": 0.65,
      "target_accuracy": 0.60,
      "gate_pass": true/false
    },
    "metastatic_cancer": { ... }
  },
  "all_gate_pass": true/false,
  "config_snapshot": { ... }
}
```

The config_snapshot field satisfies T-05-09 (Repudiation): every report includes the
full disease config dict for audit trail.

## Deviations from Plan

None — plan executed exactly as written. The plan specified exact implementation code which was followed precisely. All classes, methods, and CLI entrypoint are present as specified.

## Known Stubs

None — all implemented functionality is wired to real data and real evaluation logic.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary changes introduced.

T-05-09 mitigation applied: disease_eval_report.json includes eval_timestamp and config_snapshot for full audit trail.

T-05-08 (disease_splits.json tampering): accepted — file is rebuilt deterministically from DISEASE_RANDOM_SEED=42 if deleted.

## Self-Check: PASSED

Files verified to exist:
- src/disease_evaluator.py — created (485 lines, all 8 functions/classes present)
- data/disease_splits.json — created by CLI run in main repo

Commits verified:
- 4a06eae — feat(05-03): create DiseaseEvaluator with per-disease dataset splits
