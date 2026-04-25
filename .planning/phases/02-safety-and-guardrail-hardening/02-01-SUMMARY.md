---
phase: 02-safety-and-guardrail-hardening
plan: 01
subsystem: testing
tags: [pytest, wave-0, safety, tdd, fixtures, json]

# Dependency graph
requires:
  - phase: 01-contract-and-config-unification
    provides: MedicalVerificationConfig contract, claim_text canonical schema, conftest.py test infrastructure

provides:
  - "14 RED wave-0 test stubs in tests/test_safety_guards.py"
  - "6 shared safety fixtures in tests/conftest.py (oversized_input, duplicate_heavy_input, dangerous_claim_text, safe_clinical_text, seeds_json_path, mock_verifier_no_models)"
  - "data/dangerous_guidance_seeds.json with 5 categories and 34 seed phrases for semantic danger centroid"

affects:
  - 02-02-PLAN (config params: DANGEROUS_SEMANTIC_THRESHOLD, MAX_SUMMARY_CHARS, DUPLICATE_SENTENCE_RATIO)
  - 02-03-PLAN (ClaimExtractor: is_semantically_dangerous, danger_centroid)
  - 02-04-PLAN (MedicalVerifier: verify_single_summary input validation, degraded_mode)
  - 02-05-PLAN (export_results sidecar JSON)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED-first TDD scaffold: test stubs authored before production code"
    - "pytest.fail() as deliberate stub marker for wave-N deferred tests"
    - "ClaimExtractor.__new__() shell injection pattern for unit testing without model loading"
    - "mock_verifier_no_models fixture pattern for safe degraded-mode exercising"

key-files:
  created:
    - tests/test_safety_guards.py
    - data/dangerous_guidance_seeds.json
  modified:
    - tests/conftest.py

key-decisions:
  - "Wave 0 produces only stubs (RED); no production code changes in this plan"
  - "Seeds JSON covers 5 threat categories: medication_discontinuation, treatment_avoidance, dangerous_alternatives, emergency_minimization, vaccine_misinformation"
  - "Two tests use pytest.fail() explicitly (test_danger_flag_triggers_on_rule_match, test_max_claims_truncated_flag) because they require extract_claims_from_summary integration deferred to Wave 2"
  - "mock_verifier_no_models sets sentence_model=None and danger_centroid=None to exercise SAFE-03 degraded-mode branch without loading transformer models"

patterns-established:
  - "ClaimExtractor.__new__() shell injection: bypass __init__ then set attributes directly for unit tests"
  - "Seeds JSON structural fixture: seeds_json_path fixture returns absolute path, isolates tests from cwd"

requirements-completed: [SAFE-01, SAFE-02, SAFE-03]

# Metrics
duration: 30min
completed: 2026-04-24
---

# Phase 2 Plan 01: Safety Test Scaffold Summary

**Wave-0 RED test scaffold: 14 named pytest stubs, 6 shared fixtures, and a 5-category seeds JSON for semantic danger detection — no production code changes**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-24
- **Completed:** 2026-04-24
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `data/dangerous_guidance_seeds.json` with 5 threat categories and 34 seed phrases covering medication discontinuation, treatment avoidance, dangerous alternatives, emergency minimization, and vaccine misinformation
- Extended `tests/conftest.py` with 6 new safety fixtures (oversized_input, duplicate_heavy_input, dangerous_claim_text, safe_clinical_text, seeds_json_path, mock_verifier_no_models) without disturbing existing fixtures
- Created `tests/test_safety_guards.py` with exactly 14 pytest-collectable test stubs covering SAFE-01 (semantic danger), SAFE-02 (input validation + max claims), and SAFE-03 (degraded mode + sidecar)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create dangerous_guidance_seeds.json** - `10675ae` (chore)
2. **Task 2: Extend tests/conftest.py with safety fixtures** - `dbd88ea` (feat)
3. **Task 3: Create tests/test_safety_guards.py with 14 failing stubs** - `c3a35b6` (test)

## Files Created/Modified

- `data/dangerous_guidance_seeds.json` - 5-category seed phrase JSON for semantic danger centroid computation; 34 phrases total; loadable via json.load()
- `tests/conftest.py` - Extended with 6 new fixtures; existing fixtures and test_contracts.py suite unchanged
- `tests/test_safety_guards.py` - 14 test functions (RED by design); maps 1:1 to 02-VALIDATION.md per-task verification rows

## Decisions Made

- Seeds JSON scoped to 5 categories matching the 5 primary dangerous-guidance threat archetypes identified in 02-RESEARCH.md
- Two stubs use explicit `pytest.fail()` (test_danger_flag_triggers_on_rule_match, test_max_claims_truncated_flag) because their assertions require integration with extract_claims_from_summary which is not yet implemented; labelled "Wave 2 stub"
- `mock_verifier_no_models` patches SentenceTransformer to return None and patches ClaimExtractor._init_retriever to avoid FAISS/embedding load, enabling lightweight verifier construction in test environments

## Deviations from Plan

None - plan executed exactly as written. All three tasks completed in the correct wave-0 sequence: seeds JSON first, fixtures second, test stubs third.

## Issues Encountered

None. The `data/dangerous_guidance_seeds.json` and `tests/conftest.py` were committed in a prior agent session; this session verified both commits existed (`10675ae`, `dbd88ea`) and committed only the remaining `tests/test_safety_guards.py` stub file.

## Known Stubs

The following tests are intentionally stubbed RED and will be turned green by later wave plans:

| Test | File | Reason |
|------|------|---------|
| `test_danger_flag_triggers_on_rule_match` | tests/test_safety_guards.py:71 | Requires extract_claims_from_summary integration; deferred to 02-03 extractor plan |
| `test_max_claims_truncated_flag` | tests/test_safety_guards.py:136 | Requires MAX_CLAIMS_PER_SUMMARY enforcement in extractor; deferred to 02-03 extractor plan |

All other 12 tests will fail with AttributeError until production code is wired by waves 02-02 through 02-05.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave-0 scaffold complete; all 14 test targets named and collectable
- Plan 02-02 (config params) can begin immediately: `test_config_new_params` is the acceptance gate
- Plan 02-03 (extractor) turns green: test_semantic_danger_*, test_missing_seeds_*, test_danger_flag_triggers_on_rule_match, test_max_claims_truncated_flag
- Plan 02-04 (verifier input validation) turns green: test_input_validation_* tests
- Plan 02-05 (degraded mode + sidecar) turns green: test_degraded_mode_*, test_sidecar_* tests

---
*Phase: 02-safety-and-guardrail-hardening*
*Completed: 2026-04-24*
