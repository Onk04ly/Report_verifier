# Phase 3: Regression Safety Net - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 03-regression-safety-net
**Areas discussed:** Test file org, Risk boundary style, Confidence score approach, Dangerous-term scope

---

## Test File Organization

| Option | Description | Selected |
|--------|-------------|----------|
| One file (test_regression.py) | Single file covering TEST-01 + TEST-02 + TEST-03 in separate TestClasses. Matches one-file-per-phase pattern. | |
| Two files | test_risk_assessment.py (TEST-01 + TEST-02) and test_confidence_scoring.py (TEST-03). Cleaner separation for future growth. | ✓ |
| Extend existing | Add new TestClass blocks to test_contracts.py and/or test_safety_guards.py. No new files. | |

**User's choice:** Two files
**Notes:** None

---

## Risk Boundary Style

| Option | Description | Selected |
|--------|-------------|----------|
| Direct unit via __new__ | MedicalVerifier.__new__() + inject risk_thresholds + safety_config from real config. Feed minimal claim dicts directly. Fast, no KB/model loading. | |
| Through verify_single_summary | mock_verifier_no_models fixture + crafted text strings. Integration-style, harder to pin layer boundaries. | |
| Both | Unit for Layer 4 threshold math (direct), integration smoke for Layer 1 implausibility triggers (via verify_single_summary). | ✓ |

**User's choice:** Both

| Follow-up: Integration smoke assertions | Description | Selected |
|-----------------------------------------|-------------|----------|
| Risk level only | Assert result['risk_assessment']['level'] only. Stable against reason string changes. | ✓ |
| Risk level + reason substring | Also assert 'reason' field contains expected keywords. Brittle to formatting changes. | |
| Full result structure | Risk level, reason, stats keys, responsible_ai flags. High maintenance overhead. | |

| Follow-up: Threshold fixture source | Description | Selected |
|-------------------------------------|-------------|----------|
| Read from config (dynamic) | Call get_global_config(), compute claim counts as math(threshold * N). Stays correct if defaults change. | ✓ |
| Hardcode in fixtures | Embed threshold values (0.60, 0.40, 0.70) directly. Simpler but silently diverges on config change. | |

---

## Confidence Score Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Mock embeddings + numpy cosine | Mock get_sentence_embedding() to return fixed numpy arrays. numpy cosine (not sklearn). Assert exact label and score range. | ✓ |
| Output range only | Don't mock embeddings. Assert returned label is a valid value. Tests runs without error but doesn't pin thresholds. | |
| Test formula helpers separately | Unit-test get_evidence_weights() etc. in isolation. Avoid testing calculate_confidence_score() end-to-end. | |

**User's choice:** Mock embeddings + numpy cosine

| Follow-up: What to pin | Description | Selected |
|------------------------|-------------|----------|
| Label + score range | Assert label ('HIGH'/'MEDIUM'/'LOW') and score in [0.0, 1.0]. Stable against minor formula tweaks. | ✓ |
| Exact numeric score | Assert score == exact float. Maximum precision but brittle. | |
| Threshold crossings only | Assert HIGH input → HIGH label, LOW input → LOW label. Minimal but catches classification regressions. | |

---

## Dangerous-Term Scope

| Option | Description | Selected |
|--------|-------------|----------|
| 1-2 canonical triggers | One positive trigger + one negative per method. Minimal, fast. Pins method fires at all. | ✓ |
| One per family | Cover every named family in pattern list. Comprehensive, harder to maintain. | |
| Shared fixture string | One dense string through all methods. Compact but obscures which method covers what. | |

**User's choice:** 1-2 canonical triggers (per method)

| Follow-up: Isolation level | Description | Selected |
|---------------------------|-------------|----------|
| Direct method calls | Call _analyze_*() and _check_*() directly on __new__() shells. Same pattern as Phase 2. Fast, precise. | ✓ |
| Through _detect_medical_implausibility | Call coordinator aggregator. Tests propagation but obscures trigger source. | |
| Through _assess_overall_risk | Feed claim dicts, assert CRITICAL_RISK. End-to-end but hard to pin term family. | |

---

## Claude's Discretion

- Internal TestClass naming and exact fixture variable names
- Specific canonical trigger strings to use for each detection method
- Number of integration smoke test cases (2-4 is sufficient)

## Deferred Ideas

None — discussion stayed within phase scope.
