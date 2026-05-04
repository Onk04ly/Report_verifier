# Roadmap: Medical AI Hallucination Detection and Verification System

**Created:** 2026-04-11
**Source requirements:** `.planning/REQUIREMENTS.md`
**Granularity:** Standard

## Summary

- Phases: 6
- v1 requirements mapped: 15/15
- Coverage: 100%

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Contract and Config Unification | Remove schema/config drift in core verification flow | VERI-01, VERI-02, VERI-03 | 4 |
| 2 | Safety and Guardrail Hardening | Make safety detection and runtime guards robust | SAFE-01, SAFE-02, SAFE-03 | 4 |
| 3 | Regression Safety Net | Establish automated test coverage for critical logic | TEST-01, TEST-02, TEST-03 | 4 |
| 4 | Reproducibility and Runtime Ops | Improve artifact lineage and runtime startup behavior | DATA-01, DATA-02 | 3 |
| 5 | Disease Scope Specialization | Optimize hallucination detection for selected 2-3 diseases before scaling | FOCUS-01, FOCUS-02, FOCUS-03 | 4 |
| 6 | Documentation Alignment | Ensure docs match actual behavior and APIs | DOCS-01 | 3 |

## Phase Details

## Phase 1: Contract and Config Unification

Goal: Ensure extractor/verifier contracts and runtime tunables are explicit, centralized, and stable.

Requirements: VERI-01, VERI-02, VERI-03

Success criteria:
1. All claim/retrieval/risk thresholds are loaded from `src/medical_config.py` (no duplicate magic numbers in core path).
2. Claim objects have one canonical schema validated at module boundaries.
3. Exported verification output structure is consistent across single and batch verification flows.
4. Existing pipeline commands continue to run without output-breaking regressions.

**UI hint**: no

## Phase 2: Safety and Guardrail Hardening

Goal: Reduce unsafe false negatives and runtime misuse via stronger detection and input enforcement.

Requirements: SAFE-01, SAFE-02, SAFE-03

Success criteria:
1. Dangerous guidance detection combines rule patterns with semantic matching.
2. Input validation rejects/flags oversized or malformed summaries before heavy processing.
3. Max-claims and related extraction limits are enforced from config.
4. Degraded model availability is explicit in runtime behavior and exported results.

**UI hint**: no

## Phase 3: Regression Safety Net

Goal: Add automated tests that prevent silent quality regressions in safety-critical logic.

Requirements: TEST-01, TEST-02, TEST-03

Success criteria:
1. Risk-layer boundary tests cover each risk level and threshold edges.
2. Safety detection tests cover dangerous-term families and evidence-violation patterns.
3. Confidence scoring tests pin expected ranges/behaviors for known fixtures.
4. Tests run via one documented command and produce clear pass/fail output.

**Plans:** 3 plans

Plans:
- [ ] 03-01-PLAN.md — TEST-01: test_risk_assessment.py Layer 4 unit + integration smoke
- [ ] 03-02-PLAN.md — TEST-02: TestDangerTermDetection (5 detection methods, positive/negative)
- [ ] 03-03-PLAN.md — TEST-03: test_confidence_scoring.py (cosine mock + label/bounds)

**UI hint**: no

## Phase 4: Reproducibility and Runtime Ops

Goal: Make KB artifacts auditable and reduce recurring startup overhead.

Requirements: DATA-01, DATA-02

Success criteria:
1. KB metadata file captures generation timestamp, model IDs, and source/hash details.
2. FAISS index is persisted and reused when compatible with current embeddings.
3. Runtime includes safe fallback behavior when persisted index is stale or invalid.

**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md — DATA-01: MedicalPreprocessor writes kb_metadata.json (6-field audit record) as final preprocessing step (complete 2026-05-02)
- [x] 04-02-PLAN.md — DATA-02: ClaimExtractor FAISS persistence + hash-based staleness detection + D-02 CSV hash warning (complete 2026-05-02)

**UI hint**: no

## Phase 5: Disease Scope Specialization

Goal: Increase precision and accuracy by specializing hallucination detection to 2-3 selected diseases before broad scaling.

Requirements: FOCUS-01, FOCUS-02, FOCUS-03

Success criteria:
1. Selected disease set (2-3 diseases) is explicitly locked in config/data/evaluation artifacts.
2. Disease-specific claim and risk patterns are tuned and validated for selected diseases.
3. Evaluation reports precision and accuracy per selected disease against baseline.
4. Broad multi-disease expansion remains gated until specialist metrics meet target thresholds.

**Plans:** 4 plans

Plans:
- [x] 05-01-PLAN.md — FOCUS-01: Disease config block in medical_config.py + DiseaseKBBuckets centroid computation and KB article assignment (complete 2026-05-03)
- [x] 05-02-PLAN.md — FOCUS-02: Disease-filtered FAISS retrieval in ClaimExtractor + disease-specific Layer 1 rule patterns in MedicalVerifier (complete 2026-05-03)
- [x] 05-03-PLAN.md — FOCUS-01/FOCUS-03: Per-disease dataset splits (20/60/20 stratified) + DiseaseEvaluator with per-disease precision/accuracy report (complete 2026-05-03)
- [x] 05-04-PLAN.md — FOCUS-01/FOCUS-03: ExpansionGate with persistent run counter, consecutive-pass streak, baseline snapshot capture (complete 2026-05-03)

**UI hint**: no

## Phase 6: Documentation Alignment

Goal: Align all top-level project docs with implemented behavior and current architecture.

Requirements: DOCS-01

Success criteria:
1. Public docs accurately describe config API surface, thresholds, and phase commands.
2. Deprecated or misleading references are removed or clearly labeled.
3. README/project guidance points to the current `.planning` artifacts and workflow entrypoints.

**Plans:** 3 plans

Plans:
- [x] 06-01-PLAN.md — DOCS-01: Rewrite workflow.txt — accurate 6-phase structure with python src/ commands (complete 2026-05-04)
- [x] 06-02-PLAN.md — DOCS-01: Write README.md from scratch (absorb + delete SETUP_GUIDE.md) (complete 2026-05-04)
- [x] 06-03-PLAN.md — DOCS-01: Rewrite IMPLEMENTATION_SUMMARY.md as merged accurate reference (absorb + delete CONFIG_INTEGRATION_GUIDE.md) (complete 2026-05-04)

**UI hint**: no

## Post-v1 Expansion Gate

Broad scaling to many diseases is intentionally deferred. Expansion starts only after specialist metrics from Phase 5 are validated.

---
*Last updated: 2026-05-04 after phase 6 complete*
