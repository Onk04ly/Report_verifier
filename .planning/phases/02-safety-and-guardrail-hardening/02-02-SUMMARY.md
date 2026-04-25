---
phase: 02-safety-and-guardrail-hardening
plan: "02"
subsystem: config
tags: [safety, config, wave-1, SAFE-01, SAFE-02]
dependency_graph:
  requires: ["02-01"]
  provides: ["DANGEROUS_SEMANTIC_THRESHOLD", "MAX_SUMMARY_CHARS", "DUPLICATE_SENTENCE_RATIO"]
  affects: ["src/medical_config.py", "tests/test_safety_guards.py"]
tech_stack:
  added: []
  patterns: ["dataclass field with default", "__post_init__ validation chain"]
key_files:
  created:
    - tests/test_safety_guards.py
  modified:
    - src/medical_config.py
decisions:
  - "Added 3 new fields immediately after MAX_CLAIMS_PER_SUMMARY in the Extraction parameters block to keep related params grouped"
  - "Validation uses existing _check_probability and _check_positive_int helpers — no new validators needed"
  - "MAX_SUMMARY_CHARS uses _check_positive_int (not _check_positive_float) because char counts must be whole numbers"
metrics:
  duration_minutes: 15
  completed: "2026-04-24T14:26:40Z"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 1
---

# Phase 02 Plan 02: Config Params for Safety Hardening Summary

**One-liner:** Three new safety-tunable fields added to `ConfigurationSettings` — semantic danger threshold, input size limit, and duplicate ratio — all validated at construction time via existing `__post_init__` helpers.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing test for config new params | bc350ec | tests/test_safety_guards.py (created) |
| 1 (GREEN) | Add DANGEROUS_SEMANTIC_THRESHOLD, MAX_SUMMARY_CHARS, DUPLICATE_SENTENCE_RATIO | 0dcfef6 | src/medical_config.py |

## What Was Built

`src/medical_config.py` now exposes three new fields in `ConfigurationSettings`:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `DANGEROUS_SEMANTIC_THRESHOLD` | float | 0.75 | Cosine similarity cutoff for semantic danger-guidance centroid check (SAFE-01) |
| `MAX_SUMMARY_CHARS` | int | 5000 | Hard truncation limit applied before ClaimExtractor runs (SAFE-02a) |
| `DUPLICATE_SENTENCE_RATIO` | float | 0.5 | Fraction of duplicate sentences that triggers `repeated_content` warning (SAFE-02a) |

`MAX_CLAIMS_PER_SUMMARY = 50` is unchanged — it was already present at line 77 and was not re-added.

Validation in `__post_init__` rejects:
- `DANGEROUS_SEMANTIC_THRESHOLD` outside `[0.0, 1.0]`
- `DUPLICATE_SENTENCE_RATIO` outside `[0.0, 1.0]`
- `MAX_SUMMARY_CHARS <= 0`

`tests/test_safety_guards.py` was created as the new Phase 2 test file. The `TestConfigNewParams` class (13 tests) covers defaults, global config access, and all invalid override combinations. This file will receive additional test classes in later waves (02-03 through 02-05).

## Verification

```
pytest tests/test_safety_guards.py::TestConfigNewParams -x -v   → 13 passed
pytest tests/test_contracts.py -x -v                            → 33 passed (no regression)
```

Acceptance criteria check:
```
python -c "from src.medical_config import get_global_config; c=get_global_config(); \
  assert c.DANGEROUS_SEMANTIC_THRESHOLD==0.75 and c.MAX_SUMMARY_CHARS==5000 \
  and c.DUPLICATE_SENTENCE_RATIO==0.5 and c.MAX_CLAIMS_PER_SUMMARY==50; print('OK')"
# → OK
```

Invalid override raises `ValueError` with field name in message (verified).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The three new fields are read-ready; downstream consumers (ClaimExtractor semantic danger check, MedicalVerifier input validation) will be implemented in waves 2 and 3.

## Threat Flags

None. No new network endpoints, auth paths, or file access patterns introduced. Config field validation (T-02-03) is fully mitigated by `__post_init__` as specified in the threat register.

## Self-Check: PASSED

- `src/medical_config.py` — exists and contains all 3 new fields
- `tests/test_safety_guards.py` — exists with 13 passing tests
- Commit bc350ec (RED test) — present in git log
- Commit 0dcfef6 (GREEN impl) — present in git log
