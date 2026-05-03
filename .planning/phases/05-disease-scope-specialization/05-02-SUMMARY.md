---
phase: 05-disease-scope-specialization
plan: "02"
subsystem: disease-pipeline-wiring
tags: [disease-retrieval, layer1-patterns, faiss-filtering, implausibility, tdd, phase5]
dependency_graph:
  requires: [disease-config-block, disease-kb-buckets]
  provides: [disease-filtered-retrieval, disease-layer1-patterns, disease-aware-implausibility]
  affects: [src/claim_extractor_fixed.py, src/medical_verifier.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, numpy-boolean-mask, optional-param-backward-compat, slug-validation-via-config]
key_files:
  created:
    - tests/test_disease_retrieval.py
    - tests/test_disease_patterns.py
  modified:
    - src/claim_extractor_fixed.py
    - src/medical_verifier.py
decisions:
  - "4x candidate expansion (search_k = top_k * 4) used when disease bucket filtering is active to prevent zero-result fallback"
  - "Fallback to unfiltered top_k when zero bucket matches — prevents silent confidence degradation"
  - "self._current_claim_lower set in _detect_medical_implausibility before calling _get_disease_patterns to avoid redundant lowercasing"
  - "Slug validation uses self.global_config.DISEASE_LIST — no hardcoded slug strings in dispatch logic"
  - "_get_disease_patterns added immediately after _analyze_logical_consistency() so it is logically adjacent to Layer 1 analysis methods"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-03T09:10:23Z"
  tasks_completed: 2
  files_changed: 2
  files_created: 2
---

# Phase 05 Plan 02: Disease Pipeline Wiring Summary

## One-liner

TDD-driven wiring of disease-scope specialization into both active pipeline seams: FAISS retrieval filtering with 4x expansion in ClaimExtractor and 6 disease-specific Layer 1 implausibility/contradiction patterns (T1D + metastatic cancer) in MedicalVerifier.

## What Was Built

### Task 1: Disease-filtered retrieve_supporting_facts() in ClaimExtractor

Modified `src/claim_extractor_fixed.py` — `retrieve_supporting_facts()` now accepts an optional `disease_bucket_indices: List[int] = None` parameter.

Key implementation details:
- **4x candidate expansion**: when `disease_bucket_indices` is not None, `search_k = top_k * 4` so post-filter result count is unlikely to be zero
- **numpy boolean mask**: `mask = np.array([idx in bucket_set for idx in indices])` for efficient filtering
- **O(1) bucket lookup**: caller-supplied list converted to `set` internally: `bucket_set = set(disease_bucket_indices)`
- **Graceful fallback**: when filtering yields zero results, falls back to unfiltered `top_k` — prevents silent confidence score degradation
- **Backward-compatible**: `disease_bucket_indices=None` default means all existing call sites are unaffected
- **No new imports**: numpy and `set()` already available

### Task 2: _get_disease_patterns() and disease-aware _detect_medical_implausibility() in MedicalVerifier

Two changes to `src/medical_verifier.py`:

**Change 1 — _detect_medical_implausibility() updated:**
- New signature: `_detect_medical_implausibility(self, claim_text, disease=None)`
- `self._current_claim_lower = claim_lower` set early for use by `_get_disease_patterns()`
- After `logical_issues`, computes `disease_issues = self._get_disease_patterns(disease)` when slug is in `DISEASE_LIST`
- Slug validated: `disease is not None and disease in self.global_config.DISEASE_LIST`
- `all_issues = ... + disease_issues` — disease issues appended last, before severity auto-assignment
- `_assess_overall_risk()` call site unchanged (disease=None default = no behavioral change)

**Change 2 — _get_disease_patterns() added:**

Added immediately after `_analyze_logical_consistency()`. Returns issue dicts matching the same schema as `_analyze_medical_impossibilities()`.

| Disease | Pattern | Trigger | Severity | Type |
|---------|---------|---------|----------|------|
| type1_diabetes | Beta-cell regeneration | type 1 + diabet + (regenerate\|restore\|cure), NOT type 2 | CRITICAL | disease_specific_impossibility |
| type1_diabetes | Insulin independence | type 1 + diabet + (no insulin\|without insulin\|insulin.*free) | CRITICAL | disease_specific_contradiction |
| type1_diabetes | Universal fixed dose | type 1 + insulin + (same dose\|fixed dose\|universal dose) | HIGH | disease_specific_impossibility |
| metastatic_cancer | Cure claim | (metastatic\|stage 4\|stage iv) + cancer + (completely cured\|total cure\|eradicated\|eliminated), NOT remission | HIGH | disease_specific_contradiction |
| metastatic_cancer | Chemo avoidance | metastatic + cancer + (no chemotherapy\|without chemotherapy\|chemo.*free) + (cured\|treated\|resolved) | HIGH | disease_specific_contradiction |
| metastatic_cancer | Metastasis reversal via alt | (metastatic\|metastasis) + (reversed\|undone\|disappeared) + (diet\|supplements\|herbs\|prayer\|natural) | CRITICAL | disease_specific_impossibility |

Unknown slugs return `[]` (defensive, no exception).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) — Task 1 | 2c2b5db | test(05-02): add failing tests for disease-filtered retrieve_supporting_facts |
| GREEN (feat) — Task 1 | c3c2443 | feat(05-02): add disease_bucket_indices filtering to retrieve_supporting_facts |
| RED (test) — Task 2 | 5221a39 | test(05-02): add failing tests for _get_disease_patterns and disease-aware implausibility |
| GREEN (feat) — Task 2 | 1908bf3 | feat(05-02): add _get_disease_patterns() and disease-aware implausibility detection |

Both RED/GREEN gate pairs present in git history. No REFACTOR commits were needed.

## Test Coverage Added

| Test File | Tests | Scope |
|-----------|-------|-------|
| tests/test_disease_retrieval.py | 13 | Signature, source structure, unit logic (bucket filter, fallback, 4x expansion) |
| tests/test_disease_patterns.py | 35 | Method existence, source structure, T1D patterns (4), metastatic patterns (4), unknown slug, schema validation, _detect_medical_implausibility dispatch |

Total: 48 new tests, all passing.

## Deviations from Plan

None — plan executed exactly as written. The plan specified exact implementation code which was followed precisely.

## Known Stubs

None — all implementations are wired to real logic. The `disease_bucket_indices` parameter is designed to be passed by `MedicalVerifier.verify_for_disease()` in Plan 03; until then, all existing call sites pass `None` which is the backward-compatible no-op path.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary changes introduced.

T-05-04 mitigation in place: disease slug validated against `self.global_config.DISEASE_LIST` before `_get_disease_patterns()` is called — unknown slugs cannot inject patterns.

T-05-06 accepted: `self._current_claim_lower` is an instance variable in a single-threaded research prototype; no concurrent access risk.

## Self-Check: PASSED

Files verified to exist:
- src/claim_extractor_fixed.py — modified (contains disease_bucket_indices, search_k = top_k * 4, bucket_set, Fallback)
- src/medical_verifier.py — modified (contains _get_disease_patterns, disease=None, disease in self.global_config.DISEASE_LIST)
- tests/test_disease_retrieval.py — created
- tests/test_disease_patterns.py — created

Commits verified (in git log):
- 2c2b5db — test(05-02): RED tests for disease-filtered retrieval
- c3c2443 — feat(05-02): GREEN implementation for retrieval filtering
- 5221a39 — test(05-02): RED tests for disease patterns
- 1908bf3 — feat(05-02): GREEN implementation for disease patterns
