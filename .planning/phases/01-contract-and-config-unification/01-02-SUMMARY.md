---
phase: 01-contract-and-config-unification
plan: "02"
subsystem: verifier-boundary-and-contract-tests
tags: [schema, validation, contract, verifier, tests, export]
dependency_graph:
  requires:
    - 01-01
  provides:
    - verifier-input-boundary-validation
    - focused-contract-test-fixtures
    - deterministic-export-contract
  affects:
    - src/medical_verifier.py
    - tests/conftest.py
    - tests/test_contracts.py
tech_stack:
  added: []
  patterns:
    - "_REQUIRED_VERIFIER_CLAIM_KEYS frozenset + _validate_verifier_claim_schema() at verifier input boundary"
    - "pytest fixtures in conftest.py providing canonical valid/invalid claim payloads"
    - "_make_extractor_no_models() helper mocking _init_retriever + model loads for fast contract tests"
key_files:
  created:
    - tests/conftest.py
  modified:
    - src/medical_verifier.py
    - tests/test_contracts.py
decisions:
  - "Verifier boundary uses independent _REQUIRED_VERIFIER_CLAIM_KEYS frozenset (not imported from extractor) to enforce D-09 (validate at both boundaries)"
  - "_validate_verifier_claim_schema raises ValueError (not KeyError) listing all missing keys and naming claim_text explicitly"
  - "Contract tests fixed to mock _init_retriever and model loads via _make_extractor_no_models() helper — removes dependency on KB CSV files that are absent in worktree"
  - "TestVerifierInputBoundary requires ValueError specifically (not KeyError) — TDD RED then GREEN"
  - "TestExportStructureDeterminism pins JSON top-level keys, CSV claim_text column, safety log creation, and column set equality across single/batch exports"
metrics:
  duration: "12 minutes"
  completed: "2026-04-12"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
  files_created: 1
---

# Phase 01 Plan 02: Verifier Boundary Enforcement and Contract Tests Summary

**One-liner:** MedicalVerifier gains explicit ValueError schema validation at its input boundary; conftest.py fixtures and 33 deterministic pytest contract tests pin config, schema, verifier, and export behavior.

## What Was Built

### Task 1: Enforce claim_text at verifier input boundary (TDD)

`MedicalVerifier` in `src/medical_verifier.py` now has:

- `_REQUIRED_VERIFIER_CLAIM_KEYS = frozenset({'claim_text', 'type', 'medical_entities', 'verification_confidence', 'verification_score'})` — verifier-side schema constant, independent of the extractor's `_REQUIRED_CLAIM_KEYS` (D-09: validate at both boundaries).
- `_validate_verifier_claim_schema(claim, index)` static method — raises `ValueError` with a message that explicitly names `claim_text` and lists all missing keys when a claim payload violates the canonical schema. Raises `ValueError` not `KeyError` so callers receive a clear contract violation signal (T-01-04, D-08).
- Schema validation called at the start of `_assess_overall_risk()` before any risk or safety logic executes — all claim dicts are validated in one pass before the first plausibility check runs.

TDD flow:
- RED: Updated `TestVerifierInputBoundary` tests to require `pytest.raises(ValueError, match="claim_text")` — these failed with the prior `KeyError` behavior.
- GREEN: Added `_validate_verifier_claim_schema` and boundary call in `_assess_overall_risk` — all 3 boundary tests turned green.

### Task 2: Build focused contract fixtures and tests

`tests/conftest.py` (new):

- `_make_valid_claim(**overrides)` — canonical claim dict with all required keys plus optional fields (`has_negation`, `has_uncertainty`, `certainty_modifier`).
- `_make_invalid_claim_missing_claim_text()` — legacy `text`-keyed claim for negative path tests.
- `_make_verification_result(summary_id)` — fully populated deterministic verification result for export tests.
- pytest fixtures: `valid_claim`, `valid_claims_list`, `invalid_claim_missing_claim_text`, `invalid_claim_empty`, `deterministic_verification_result`, `deterministic_verification_result_list`.

`tests/test_contracts.py` (updated):

- Fixed `TestExtractorReadsGlobalConfig` tests: replaced direct `ClaimExtractor(config=None)` calls (which triggered real model/CSV loads) with `_make_extractor_no_models()` helper that patches `spacy.load`, `AutoTokenizer`, `AutoModel`, and `_init_retriever`. Tests now run in ~2 seconds without any data files.
- Added `TestVerifierInputBoundary` (4 tests): pins that `_assess_overall_risk` raises `ValueError` with `claim_text` for missing key, empty dict, and legacy `text`-only payload; confirms valid canonical claim succeeds.
- Added `TestExportStructureDeterminism` (6 tests): pins JSON top-level keys (`metadata`, `verification_results`, `global_safety_summary`), required metadata fields, CSV `claim_text` column (not legacy `text`), deterministic column set across single and batch exports, safety log creation alongside every export.
- Total: 33 tests, all green.

### Task 3: Confirm runtime smoke path and export determinism

Verified via in-process smoke check (full `python src/medical_verifier.py` requires spaCy + KB data files not present in the parallel worktree environment):

1. `_assess_overall_risk` raises `ValueError` with `claim_text` for malformed claim — confirmed.
2. Risk assessment produces `{"level": "LOW_RISK", ...}` for canonical claim — confirmed.
3. `export_results` produces `metadata`, `verification_results`, `global_safety_summary` keys in JSON and writes `_safety_log.json` alongside — confirmed.
4. No `claim['text']` legacy references remain in `src/medical_verifier.py` — confirmed by grep.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing contract tests failed due to real model/data loads**
- **Found during:** Task 1 — first test run showed `TestExtractorReadsGlobalConfig::test_none_config_resolves_to_global_config` failing with `FileNotFoundError` on KB CSV
- **Issue:** Module-level `sys.modules` mocks in `test_contracts.py` did not prevent `spacy.load()` from succeeding (spaCy is installed) nor `pd.read_csv` from attempting to load KB CSV (not present in worktree). The mocks only worked for non-installed packages.
- **Fix:** Replaced direct `ClaimExtractor(config=None)` instantiation in tests with `_make_extractor_no_models()` helper that patches `ClaimExtractor._init_retriever`, `spacy.load`, `AutoTokenizer.from_pretrained`, and `AutoModel.from_pretrained` at method level — making tests fully self-contained.
- **Files modified:** `tests/test_contracts.py`
- **Commit:** 8e5807c

**2. [Rule 2 - Missing critical functionality] TDD RED phase required stricter test assertions**
- **Found during:** Task 1 TDD implementation — initial test allowed `(ValueError, KeyError)` which passed even with the pre-existing `KeyError` behavior
- **Issue:** Allowing `KeyError` did not enforce the contract requirement (D-08: schema mismatch must be a hard error with explicit message, not silent fallback or opaque key error)
- **Fix:** Tightened `TestVerifierInputBoundary` assertions to `pytest.raises(ValueError, match="claim_text")` — this was the proper RED state that drove the implementation of `_validate_verifier_claim_schema`
- **Files modified:** `tests/test_contracts.py`
- **Commit:** 8e5807c

## Known Stubs

None — all changes wire real validation behavior. No placeholder data or hardcoded empty values were introduced.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at external trust boundaries. The changes harden an existing internal boundary (claim payloads entering verifier risk layer) and add test infrastructure that uses only synthetic data (T-01-06: accepted disposition).

## Verification

- `pytest tests/test_contracts.py -x -v` — 33/33 passed in ~2 seconds
- Verifier boundary: `ValueError` with `claim_text` raised for any claim missing required keys
- Export determinism: JSON top-level shape, CSV `claim_text` column, safety log creation all pinned by regression tests
- No `claim['text']` or `claim.get('text', ...)` legacy accesses remain in `src/medical_verifier.py`
- `_REQUIRED_VERIFIER_CLAIM_KEYS` is an independent frozenset in the verifier (D-09: both boundaries validate)

## Self-Check: PASSED

Files confirmed present:
- `src/medical_verifier.py` — exists, updated with boundary validation
- `tests/conftest.py` — exists, new fixtures file
- `tests/test_contracts.py` — exists, 33 tests green

Commits confirmed:
- `8e5807c` — feat(01-02): enforce claim_text at verifier boundary and add contract fixtures
