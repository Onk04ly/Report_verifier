---
phase: 01-contract-and-config-unification
plan: "01"
subsystem: config-and-extraction
tags: [config, schema, validation, contract, extractor]
dependency_graph:
  requires: []
  provides:
    - validated-central-config
    - canonical-claim-schema
  affects:
    - src/medical_config.py
    - src/claim_extractor_fixed.py
    - src/medical_verifier.py
tech_stack:
  added:
    - pytest (contract test suite)
  patterns:
    - ConfigurationSettings.__post_init__ validation with explicit error lists
    - Frozen required-key schema enforcement at extractor output boundary
    - Full config object injection (ConfigurationSettings) replacing partial dict passing
key_files:
  created:
    - tests/__init__.py
    - tests/test_contracts.py
  modified:
    - src/medical_config.py
    - src/claim_extractor_fixed.py
    - src/medical_verifier.py
decisions:
  - "Config validation at __post_init__ lists ALL invalid fields in one error, not just the first"
  - "Evidence weights sum-to-1 invariant is checked with 1e-6 floating-point tolerance"
  - "ClaimExtractor refuses plain dicts via TypeError before any model load work begins"
  - "Schema validation occurs at both claim construction point and extract_claims_from_summary output boundary"
  - "MedicalVerifier now passes the full ConfigurationSettings object to ClaimExtractor, not get_confidence_thresholds() dict"
metrics:
  duration: "8 minutes"
  completed: "2026-04-12"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
  files_created: 2
---

# Phase 01 Plan 01: Contract and Config Unification Summary

**One-liner:** ConfigurationSettings gains __post_init__ validation and extractor distance constants; ClaimExtractor drops its local fallback dict and enforces claim_text-only output with boundary schema checks.

## What Was Built

### Task 1: Move extractor tunables into validated config

`ConfigurationSettings` in `src/medical_config.py` now:

- Validates every field in `__post_init__`, raising a single `ValueError` that lists all invalid key+value pairs at once (D-02, D-05, T-01-01).
- Adds five new extractor-specific constants that were previously hardcoded inline in `ClaimExtractor` scoring logic (D-03):
  - `DISTANCE_NORM_DIVISOR = 100.0` — divisor for FAISS L2 distance normalization
  - `OUTLIER_DISTANCE_THRESHOLD = 35.0` — minimum distance before outlier penalty applies
  - `OUTLIER_PENALTY_BASE = 0.2` — base penalty value for outliers
  - `OUTLIER_PENALTY_SCALING = 0.005` — linear scaling factor per distance unit beyond threshold
  - `OUTLIER_PENALTY_CAP = 0.4` — maximum outlier penalty
- Adds `get_outlier_params()` accessor returning all five constants as a dict.

`ClaimExtractor.__init__` in `src/claim_extractor_fixed.py` now:

- Accepts only `ConfigurationSettings` or `None` (D-01, T-01-02). Passing a plain dict raises `TypeError` immediately, before any model is loaded.
- When `None` is passed, resolves to `get_global_config()`.
- Replaced all `self.config['key']` dict accesses with `self.config.ATTRIBUTE` reads throughout: `TOP_K_FACTS`, `CONFIDENCE_FACTS_COUNT`, `MIN_SENTENCE_LENGTH`, `DISTANCE_NORM_DIVISOR`, and `get_evidence_weights()`, `get_confidence_thresholds()`, `get_outlier_params()`.

`MedicalVerifier.__init__` in `src/medical_verifier.py` now:

- Passes the full `ConfigurationSettings` object to `ClaimExtractor` (not the partial `get_confidence_thresholds()` dict).
- Rejects any non-`ConfigurationSettings` value for `extractor_config` with a `TypeError`.

### Task 2: Emit canonical claim_text and reject schema drift

`identify_medical_claims()` in `src/claim_extractor_fixed.py` now:

- Emits `claim_text` instead of the legacy `text` key in every claim dict (D-07, D-11, T-01-03).
- Calls `_validate_claim_schema()` immediately after constructing each claim dict (construction-point validation).

`extract_claims_from_summary()` in `src/claim_extractor_fixed.py` now:

- Re-validates every claim at the output boundary before returning, catching any claim that bypasses `identify_medical_claims` (D-08, D-09).

`_assess_overall_risk()` in `src/medical_verifier.py` now:

- Uses `claim['claim_text']` directly (hard access, no fallback) instead of `claim.get('text', claim.get('claim_text', ''))` (D-08, D-11).

CSV export in `export_results()` in `src/medical_verifier.py` now:

- Uses `claim['claim_text']` instead of `claim['text']`.

Module-level schema constants in `src/claim_extractor_fixed.py`:

- `_REQUIRED_CLAIM_KEYS = frozenset({'claim_text', 'type', 'medical_entities', 'verification_confidence', 'verification_score'})` — immutable, single definition.
- `_validate_claim_schema(claim, context)` — raises `ValueError` listing all missing keys with an optional context label.

### Contract tests

`tests/test_contracts.py` — 23 pytest tests covering:
- VERI-01: extractor reads global config only, rejects dict/string/None-then-resolves
- VERI-02: claim schema requires `claim_text`, rejects legacy `text`, lists all missing keys
- Config validation: rejects bad confidence thresholds, weight sums, zero TOP_K_FACTS, negative divisors
- Verifier contract: rejects dict extractor_config

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] MedicalVerifier passed a partial dict to ClaimExtractor**
- **Found during:** Task 1 implementation
- **Issue:** `MedicalVerifier.__init__` called `self.global_config.get_confidence_thresholds()` and passed the resulting dict to `ClaimExtractor`. After Task 1 made `ClaimExtractor` reject non-`ConfigurationSettings` args, this would break the verifier immediately.
- **Fix:** Updated `MedicalVerifier.__init__` to pass the full `ConfigurationSettings` object and added an explicit `isinstance` guard that raises `TypeError` for any other type.
- **Files modified:** `src/medical_verifier.py`
- **Commit:** 1376d35

**2. [Rule 2 - Missing critical functionality] test_claim_extraction used inline dict config**
- **Found during:** Task 1 review
- **Issue:** The `test_claim_extraction()` function at the bottom of `claim_extractor_fixed.py` still constructed an inline config dict and passed it to `ClaimExtractor`, violating D-01 and breaking under the new type guard.
- **Fix:** Replaced the inline dict with `get_global_config()`.
- **Files modified:** `src/claim_extractor_fixed.py`
- **Commit:** 1376d35

## Known Stubs

None — all changes wire real behavior. No placeholder data or hardcoded empty values were introduced.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at external trust boundaries were introduced. The changes harden an existing internal boundary (config -> extractor) and an existing internal boundary (extractor output -> verifier input).

## Verification

- `python -m pytest tests/test_contracts.py -x -v` — 23/23 passed
- Config singleton validates at import time; bad defaults fail before any code runs
- `ClaimExtractor(config=None)` initializes successfully using global config (models loaded, FAISS indexed)
- All `self.config['key']` dict-style accesses eliminated from extractor scoring paths

## Self-Check: PASSED

Files confirmed present:
- `src/medical_config.py` — exists, updated
- `src/claim_extractor_fixed.py` — exists, updated
- `src/medical_verifier.py` — exists, updated
- `tests/test_contracts.py` — exists, 23 tests green
- `tests/__init__.py` — exists

Commits confirmed:
- `1376d35` — feat(01-01): move extractor tunables into validated config and wire full config object
