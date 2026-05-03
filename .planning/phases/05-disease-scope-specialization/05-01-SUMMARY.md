---
phase: 05-disease-scope-specialization
plan: "01"
subsystem: disease-config
tags: [config, disease-buckets, centroids, phase5, tdd]
dependency_graph:
  requires: []
  provides: [disease-config-block, disease-kb-buckets, disease-centroids-npz]
  affects: [src/medical_config.py, src/disease_buckets.py, data/disease_centroids.npz]
tech_stack:
  added: []
  patterns: [dataclass-config, cosine-centroid-bucketing, normalized-embedding-dot-product]
key_files:
  created:
    - src/disease_buckets.py
    - data/disease_centroids.npz
  modified:
    - src/medical_config.py
decisions:
  - "Cosine similarity threshold 0.60 used for KB bucket assignment per D-04"
  - "Top-20 highest-quality articles used for centroid computation per D-04"
  - "Overlap resolution: article assigned to disease with highest cosine sim (D-05)"
  - "CLI uses git common-dir to resolve data paths when running from worktree"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-03T08:56:39Z"
  tasks_completed: 2
  files_changed: 2
  files_created: 2
---

# Phase 05 Plan 01: Disease Config and KB Buckets Summary

## One-liner

TDD-driven Phase 5 disease-scope specialization foundation: locked disease config block in ConfigurationSettings and cosine-centroid KB bucketing producing 4,042 T1D and 20,689 metastatic-cancer articles.

## What Was Built

### Task 1: Phase 5 disease-specialization config block (GREEN phase of TDD)

Added a clearly labelled `# Phase 5 — Disease Scope Specialization` block to `src/medical_config.py` (`ConfigurationSettings` dataclass), completing the GREEN phase for the 36 TDD tests committed in the prior wave.

Fields added:
- `DISEASE_LIST: list` — locked to `["type1_diabetes", "metastatic_cancer"]`
- `DISEASE_CENTROID_SIM_THRESHOLD: float = 0.60`
- `DISEASE_CENTROID_TOP_K: int = 20`
- `EXPANSION_GATE_N: int = 5`
- `EXPANSION_GATE_CONSECUTIVE: int = 2`
- `DISEASE_RANDOM_SEED: int = 42`
- `DISEASE_PRECISION_TARGET: float = 0.65`
- `DISEASE_ACCURACY_TARGET: float = 0.60`
- `HOLDOUT_FRACTION: float = 0.20`
- `TUNE_FRACTION: float = 0.20`
- `TRAIN_FRACTION: float = 0.60`

`__post_init__` validation added for all 11 fields including:
- DISEASE_LIST must be a non-empty list
- HOLDOUT + TUNE + TRAIN must sum to 1.0 (±1e-6)
- All numeric fields validated via existing `_check_probability` / `_check_positive_int` helpers

`get_disease_config()` accessor method added returning all 11 fields as `Dict[str, Any]`.

All 36 pre-existing TDD tests now pass (0 failures introduced).

### Task 2: disease_buckets.py — centroid computation and KB article assignment

Created `src/disease_buckets.py` as a lightweight standalone module (no ClaimExtractor, no faiss dependency).

Key components:
- `DISEASE_CATEGORY_KEYWORDS` — maps disease slugs to KB `category` column values
- `DiseaseKBBuckets` dataclass — centroids, article_indices, config_snapshot
- `build_disease_buckets(kb_csv_path, embeddings_path, config=None)` — full pipeline:
  - Loads KB CSV (category + quality_score columns only)
  - Memory-maps `kb_embeddings_preprocessed.npy`, normalizes all vectors
  - Per disease: selects top-20 quality candidates, computes and re-normalizes centroid
  - Assigns all KB articles via batch dot product against centroid (threshold 0.60)
  - Resolves overlaps: each article kept only in the bucket with higher cosine sim
- `save_disease_buckets()` — persists centroids and article index arrays to `.npz`
- `load_disease_buckets()` — reconstructs DiseaseKBBuckets from `.npz`
- CLI entrypoint with git-worktree-aware path resolution

## Article Counts Per Disease Bucket

| Disease | Articles Assigned |
|---------|------------------|
| type1_diabetes | 4,042 |
| metastatic_cancer | 20,689 |
| Overlapping articles | 0 (all resolved) |

## Centroid File

- Path: `data/disease_centroids.npz`
- Keys: `type1_diabetes` (768,), `metastatic_cancer` (768,), `type1_diabetes_indices`, `metastatic_cancer_indices`

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 6c669e6 | test(05-01): add failing tests for Phase 5 disease-config fields and validation |
| GREEN (feat) | da6911c | feat(05-01): implement Phase 5 disease-config block in ConfigurationSettings |

Both TDD gates present in git history. No REFACTOR commit was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CLI path resolution for git worktree**
- **Found during:** Task 2 CLI verification
- **Issue:** When running `python src/disease_buckets.py` from the worktree directory, the computed repo root pointed to the worktree (which has `data/` but only git-tracked files, not large pre-computed artifacts)
- **Fix:** Added worktree-aware path detection in CLI entrypoint: checks if KB CSV exists at computed root; if not, resolves via `git rev-parse --git-common-dir` to find the main repo root where large data files live
- **Files modified:** `src/disease_buckets.py` (CLI block only)
- **Commit:** c7c014f

## Known Stubs

None — all implemented functionality is wired to real data.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary changes introduced. All file access is local read-only (KB CSV + .npy) with explicit `FileNotFoundError` guards (mitigating T-05-03). `data/disease_centroids.npz` is a local research artifact (T-05-01: accepted). No PII or sensitive data in `DISEASE_LIST` (T-05-02: accepted).

## Self-Check: PASSED

Files verified to exist:
- src/medical_config.py — modified (contains DISEASE_LIST, get_disease_config)
- src/disease_buckets.py — created
- data/disease_centroids.npz — created by CLI run (in main repo)

Commits verified:
- da6911c — feat(05-01): implement Phase 5 disease-config block
- c7c014f — feat(05-01): create disease_buckets.py
