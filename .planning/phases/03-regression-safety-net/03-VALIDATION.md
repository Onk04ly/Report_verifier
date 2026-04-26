---
phase: 3
slug: regression-safety-net
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none — pytest auto-discovers `tests/` |
| **Quick run command** | `pytest tests/test_risk_assessment.py tests/test_confidence_scoring.py -x -v` |
| **Full suite command** | `pytest tests/ -x -v` |
| **Estimated runtime** | ~8 seconds (baseline 5.11 s + new tests) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_risk_assessment.py tests/test_confidence_scoring.py -x -v`
- **After every plan wave:** Run `pytest tests/ -x -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | TEST-01 | — | Layer 4 HIGH_RISK fires at low_conf_ratio >= threshold | unit | `pytest tests/test_risk_assessment.py::TestRiskAssessmentLayer4 -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | TEST-01 | — | Layer 4 MEDIUM_RISK fires at correct threshold band | unit | `pytest tests/test_risk_assessment.py::TestRiskAssessmentLayer4 -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | TEST-01 | — | Layer 4 LOW_RISK fires at high_conf_ratio >= threshold | unit | `pytest tests/test_risk_assessment.py::TestRiskAssessmentLayer4 -x` | ❌ W0 | ⬜ pending |
| 3-01-04 | 01 | 1 | TEST-01 | — | Integration: known-bad hallucination text → CRITICAL_RISK | integration | `pytest tests/test_risk_assessment.py::TestRiskAssessmentIntegration -x` | ❌ W0 | ⬜ pending |
| 3-01-05 | 01 | 1 | TEST-01 | — | Integration: known-good clinical text → LOW_RISK | integration | `pytest tests/test_risk_assessment.py::TestRiskAssessmentIntegration -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 01 | 1 | TEST-02 | — | `_analyze_medical_impossibilities()` fires on positive trigger | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 01 | 1 | TEST-02 | — | `_analyze_patient_safety_risks()` fires on positive trigger | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | ❌ W0 | ⬜ pending |
| 3-02-03 | 01 | 1 | TEST-02 | — | `_analyze_evidence_contradictions()` fires on positive trigger | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | ❌ W0 | ⬜ pending |
| 3-02-04 | 01 | 1 | TEST-02 | — | `_check_biological_impossibilities_optimized()` returns penalty > 0 | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | ❌ W0 | ⬜ pending |
| 3-02-05 | 01 | 1 | TEST-02 | — | `_check_evidence_based_violations_optimized()` returns penalty > 0 | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | ❌ W0 | ⬜ pending |
| 3-03-01 | 02 | 1 | TEST-03 | — | `calculate_confidence_score()` returns HIGH for identical vectors | unit | `pytest tests/test_confidence_scoring.py -x` | ❌ W0 | ⬜ pending |
| 3-03-02 | 02 | 1 | TEST-03 | — | `calculate_confidence_score()` returns LOW for absent/orthogonal facts | unit | `pytest tests/test_confidence_scoring.py -x` | ❌ W0 | ⬜ pending |
| 3-03-03 | 02 | 1 | TEST-03 | — | Returned score is in [0.0, 1.0] and label is valid string | unit | `pytest tests/test_confidence_scoring.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_risk_assessment.py` — empty file with class stubs for TestRiskAssessmentLayer4, TestRiskAssessmentIntegration, TestDangerTermDetection (REQ: TEST-01, TEST-02)
- [ ] `tests/test_confidence_scoring.py` — empty file with class stub for TestConfidenceScoring (REQ: TEST-03)

*Both new files are the primary Phase 3 deliverables and do not exist yet.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
