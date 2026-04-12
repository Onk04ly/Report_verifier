---
phase: 01-contract-and-config-unification
type: gap-fix-summary
date: 2026-04-12
status: resolved
gaps_fixed: 2
commits:
  - hash: 06892cc
    message: "feat(01-gap): move inline scoring constants to MedicalVerificationConfig"
  - hash: 6218cb6
    message: "fix(01-gap): update report_generator to use canonical claim_text key"
---

# Phase 1 Gap Fix Summary

## Context

Phase 1 verification (`01-VERIFICATION.md`) identified two gaps blocking full SC1 satisfaction:

1. ~20 inline scoring constants remained hardcoded in `claim_extractor_fixed.py` core confidence and penalty paths, violating D-03 and D-04.
2. `report_generator.py` accessed `claim['text']` (legacy key), violating D-07 and D-14.

---

## Gap 1: Move Inline Scoring Constants to MedicalVerificationConfig

**Files changed:** `src/medical_config.py`, `src/claim_extractor_fixed.py`
**Commit:** `06892cc`

### Constants Added to ConfigurationSettings

**Evidence grade weights** (previously `grade_weights = {'A': 1.0, ...}` inline in `calculate_confidence_score`):
- `GRADE_WEIGHT_A = 1.0`
- `GRADE_WEIGHT_B = 0.8`
- `GRADE_WEIGHT_C = 0.6`
- `GRADE_WEIGHT_D = 0.4`
- Accessor: `get_grade_weights()` returns the letter-to-float mapping dict

**Plausibility penalty levels** (previously bare floats in all `_check_*_optimized` sub-methods):
- `PLAUSIBILITY_PENALTY_CRITICAL = 1.0`
- `PLAUSIBILITY_PENALTY_VERY_HIGH = 0.95`
- `PLAUSIBILITY_PENALTY_HIGH = 0.9`
- `PLAUSIBILITY_PENALTY_MEDIUM_HIGH = 0.8`
- `PLAUSIBILITY_PENALTY_MEDIUM = 0.7`
- `PLAUSIBILITY_PENALTY_LOW = 0.6`

**Evidence absence penalty constants** (previously bare floats/ints in `_detect_evidence_absence_penalty`):
- `EVIDENCE_ABSENCE_PENALTY_NO_FACTS = 0.8`
- `EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_2 = 0.4`
- `EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_1 = 0.2`
- `EVIDENCE_ABSENCE_DIST_CRITICAL = 25.0`
- `EVIDENCE_ABSENCE_PENALTY_DIST_HIGH = 0.5`
- `EVIDENCE_ABSENCE_DIST_HIGH = 20.0`
- `EVIDENCE_ABSENCE_PENALTY_DIST_MEDIUM = 0.3`
- `EVIDENCE_ABSENCE_DIST_ALL_IRRELEVANT = 30.0`
- `EVIDENCE_ABSENCE_PENALTY_ALL_IRRELEVANT = 0.7`

**Negation/uncertainty multipliers** (previously bare floats in `identify_medical_claims`):
- `NEGATION_CONFIDENCE_BASE_HIGH = 0.8`
- `NEGATION_CONFIDENCE_BASE_LOW = 0.6`
- `NEGATION_CONFIDENCE_PENALTY = 0.7`
- `UNCERTAINTY_CONFIDENCE_PENALTY = 0.6`

### Validation Added

All new fields validated in `__post_init__` using existing `_check_probability` and `_check_positive_float` helpers. Invalid values raise `ValueError` at construction time with the field name listed.

### Behavior Preserved

Numeric values are identical to the previous inline literals. No scoring behavior changed — only the source of truth moved from inline code to `ConfigurationSettings`.

---

## Gap 2: Fix report_generator.py Legacy claim Key

**Files changed:** `src/report_generator.py`
**Commit:** `6218cb6`

**Change:** Line 282: `claim['text']` → `claim['claim_text']`

This was the only `claim['text']` access in the file. The fix aligns `report_generator.py` with D-07 (canonical key is `claim_text`) and D-14 (fix immediate caller files that break due to contract changes). Without this fix, `report_generator.py` would raise `KeyError` when receiving claims from the updated extractor.

---

## Verification After Fixes

| Check | Result |
|-------|--------|
| `pytest tests/test_contracts.py -v` | 33/33 passed in 3.22s |
| `from src.medical_config import get_global_config` | Config OK |
| Config attributes accessible | `GRADE_WEIGHT_A=1.0`, `PLAUSIBILITY_PENALTY_CRITICAL=1.0`, `EVIDENCE_ABSENCE_DIST_CRITICAL=25.0`, `NEGATION_CONFIDENCE_BASE_HIGH=0.8` |
| `from claim_extractor_fixed import ClaimExtractor` (with mocked deps) | Extractor OK |
| Remaining bare literals in scoring paths | None (only `0.5` fallback in `.get()` calls and `1.0` cap in `min()`) |

---

## SC1 Status After Fixes

**SATISFIED.** All runtime scoring constants used by the extractor core confidence and penalty path are now sourced from `ConfigurationSettings`. The verification gap identified in `01-VERIFICATION.md` is fully resolved.
