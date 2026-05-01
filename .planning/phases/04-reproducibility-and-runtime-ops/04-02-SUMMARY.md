---
phase: 04-reproducibility-and-runtime-ops
plan: "02"
subsystem: claim-extractor
tags:
  - faiss-persistence
  - staleness-detection
  - data-integrity
  - sha256
dependency_graph:
  requires:
    - DATA-01 (kb_metadata.json written by medical_preprocessor — used for hash lookup)
  provides:
    - FAISS index persisted to data/faiss_index.bin
    - Staleness metadata in data/faiss_index.meta
    - D-02 CSV hash warning at ClaimExtractor startup
  affects:
    - src/claim_extractor_fixed.py (ClaimExtractor._init_retriever startup path)
    - tests/conftest.py (documentation annotation)
tech_stack:
  added:
    - hashlib (stdlib, SHA-256 computation)
    - datetime (stdlib, UTC ISO 8601 timestamps)
  patterns:
    - Hash-based cache invalidation (faiss_index.meta embeddings_sha256 vs kb_metadata.json)
    - Warn-and-rebuild fallback (corrupt or stale index degrades gracefully)
    - GPU-to-CPU transfer before faiss.write_index serialization
key_files:
  modified:
    - src/claim_extractor_fixed.py
    - tests/conftest.py
  creates_at_runtime:
    - data/faiss_index.bin (FAISS index written after first build)
    - data/faiss_index.meta (companion JSON with embeddings_sha256 + built_at)
decisions:
  - "D-04: staleness check is hash-based; faiss_index.meta stores embeddings_sha256 used at build time"
  - "D-05: artifacts at data/faiss_index.bin and data/faiss_index.meta"
  - "D-06: stale/missing/corrupt path prints warning then rebuilds; never crashes"
  - "D-07: always save both artifacts after a successful rebuild"
  - "D-02: CSV hash warning is non-blocking; print and continue if mismatch detected"
  - "SHA-256 chunk size: 8 KB (idiomatic, works for large .npy files)"
  - "GPU-to-CPU transfer: uses faiss.index_gpu_to_cpu if attribute exists; try/except falls back silently"
metrics:
  duration: "2 minutes"
  completed: "2026-05-01T10:30:04Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
  tests_before: 83
  tests_after: 83
  test_regressions: 0
---

# Phase 4 Plan 02: FAISS Persistence with Hash-Based Staleness Detection Summary

**One-liner:** FAISS index persisted to `data/faiss_index.bin` after first build, reloaded on subsequent cold starts using SHA-256 staleness check against `kb_metadata.json` or live `.npy` hash, with warn-and-rebuild fallback for stale, missing, or corrupt indexes.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _compute_sha256, _save_faiss_artifacts, _load_or_build_faiss_index to ClaimExtractor | a9ae9bb | src/claim_extractor_fixed.py |
| 2 | Annotate conftest.py with DATA-02 FAISS mock coverage notes | 416ff94 | tests/conftest.py |

## What Was Built

### Task 1: FAISS Persistence in ClaimExtractor

Three new methods added to `ClaimExtractor` in `src/claim_extractor_fixed.py`:

**`_compute_sha256(path)`** — reads a file in 8 KB chunks and returns its SHA-256 hex digest. Raises `FileNotFoundError` if path is absent.

**`_save_faiss_artifacts(embeddings_sha256)`** — writes `data/faiss_index.bin` via `faiss.write_index` and `data/faiss_index.meta` (JSON with `embeddings_sha256` + `built_at` UTC ISO 8601). GPU indexes are transferred to CPU via `faiss.index_gpu_to_cpu` before serialization. All I/O is wrapped in try/except — failures print a warning and continue.

**`_load_or_build_faiss_index(embeddings_path)`** — the main entry point replacing both former direct calls to `_create_optimized_faiss_index()` in `_init_retriever()`. Logic:
1. Resolve `current_sha256` from `kb_metadata.json` if it exists; otherwise compute live from `.npy` file
2. If `faiss_index.bin` + `faiss_index.meta` exist and `saved_sha256 == current_sha256` → load from disk, print "FAISS index loaded from disk (hash verified)"
3. If stale → print "FAISS index stale or missing — rebuilding from embeddings", rebuild
4. If corrupt (faiss.read_index raises) → print "FAISS index corrupt — rebuilding from embeddings", rebuild
5. After any rebuild → call `_save_faiss_artifacts(current_sha256)` to persist new artifacts

**D-02 CSV hash warning** added immediately after `self.kb = pd.read_csv(...)` in `_init_retriever()`. Reads `kb_metadata.json`, compares `csv_sha256` against live SHA-256 of the preprocessed CSV. If mismatch: prints "WARNING: KB file hash mismatch — metadata may be stale". Non-blocking.

### Task 2: conftest.py Annotation

Added a documentation comment above the `_HEAVY_MODULES` loop explaining that the `"faiss"` `MagicMock` already covers `faiss.write_index`, `faiss.read_index`, `faiss.IndexFlatL2`, and `faiss.get_num_gpus`. Notes that tests directly exercising `_load_or_build_faiss_index()` should additionally patch `os.path.exists` and `builtins.open`. The existing `mock.patch.object(ClaimExtractor, "_init_retriever", return_value=None)` pattern in `mock_verifier_no_models` prevents all FAISS I/O during test construction — no existing fixtures required changes.

## Verification Results

```
83 passed, 11 warnings in 1.41s   (0 regressions)
```

Key pattern presence confirmed:
- `_compute_sha256`: 3 occurrences (definition + 2 call sites)
- `_save_faiss_artifacts`: 2 occurrences (definition + call in _load_or_build_faiss_index)
- `_load_or_build_faiss_index`: 3 occurrences (definition + 2 call sites replacing former _create_optimized_faiss_index calls)
- `faiss.write_index`: present in _save_faiss_artifacts
- `faiss_index.bin` and `faiss_index.meta`: present as path strings
- "stale or missing": 2 occurrences (two code paths)
- "KB file hash mismatch": present (D-02 warning)
- "corrupt": present (corrupt fallback message)
- `hashlib` and `datetime`: imported

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The persistence layer wires directly to `faiss.write_index`/`faiss.read_index` and `json.dump`/`json.load`. No placeholder values remain.

## Threat Flags

None. All STRIDE threats T-04-02-01 through T-04-02-04 are addressed by mitigations implemented in this plan:
- T-04-02-01 (Tampering, faiss_index.bin): hash-based staleness check implemented
- T-04-02-02 (Tampering, faiss_index.meta): sha256 comparison covers forced-match tamper attempt at research-tool severity
- T-04-02-03 (DoS, corrupt index): try/except around faiss.read_index with warn-and-rebuild fallback
- T-04-02-04 (Information Disclosure, SHA-256 hashes): accepted — artifact fingerprints, no sensitive data

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/claim_extractor_fixed.py | FOUND |
| tests/conftest.py | FOUND |
| 04-02-SUMMARY.md | FOUND |
| Commit a9ae9bb (Task 1) | FOUND |
| Commit 416ff94 (Task 2) | FOUND |
