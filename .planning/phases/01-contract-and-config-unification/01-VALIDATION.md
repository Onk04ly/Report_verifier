---
phase: 01
slug: contract-and-config-unification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 01 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none - Wave 0 installs |
| **Quick run command** | `python src/medical_verifier.py` |
| **Full suite command** | `pytest tests/test_contracts.py -x` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python src/medical_verifier.py`
- **After every plan wave:** Run `pytest tests/test_contracts.py -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | VERI-01 | T-01-01 | Runtime tunables read from centralized config only | unit | `pytest tests/test_contracts.py::test_extractor_reads_global_config -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | VERI-02 | T-01-02 | Claim schema enforces canonical `claim_text` key at both boundaries | unit | `pytest tests/test_contracts.py::test_claim_schema_requires_claim_text -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 2 | VERI-03 | T-01-03 | Export structure deterministic for downstream consumers | integration | `pytest tests/test_contracts.py::test_export_shape_is_deterministic -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 2 | VERI-01, VERI-03 | T-01-04 | Smoke path runs without contract regressions | smoke | `python src/medical_verifier.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_contracts.py` - contract tests for VERI-01/02/03
- [ ] `tests/conftest.py` - shared test fixtures for small synthetic claim payloads
- [ ] `pytest` install in environment - required before full suite command can pass

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Verify no immediate breakage in notebook/script callers touched by schema change | VERI-02, VERI-03 | Caller surfaces vary and may not have automated coverage yet | Run affected script/notebook entry path once and confirm canonical `claim_text` handling |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

