# Roadmap: Medical AI Hallucination Detection and Verification System

**Created:** 2026-04-11
**Source requirements:** `.planning/REQUIREMENTS.md`
**Granularity:** Standard

## Summary

- Phases: 5
- v1 requirements mapped: 12/12
- Coverage: 100%

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Contract and Config Unification | Remove schema/config drift in core verification flow | VERI-01, VERI-02, VERI-03 | 4 |
| 2 | Safety and Guardrail Hardening | Make safety detection and runtime guards robust | SAFE-01, SAFE-02, SAFE-03 | 4 |
| 3 | Regression Safety Net | Establish automated test coverage for critical logic | TEST-01, TEST-02, TEST-03 | 4 |
| 4 | Reproducibility and Runtime Ops | Improve artifact lineage and runtime startup behavior | DATA-01, DATA-02 | 3 |
| 5 | Documentation Alignment | Ensure docs match actual behavior and APIs | DOCS-01 | 3 |

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

**UI hint**: no

## Phase 4: Reproducibility and Runtime Ops

Goal: Make KB artifacts auditable and reduce recurring startup overhead.

Requirements: DATA-01, DATA-02

Success criteria:
1. KB metadata file captures generation timestamp, model IDs, and source/hash details.
2. FAISS index is persisted and reused when compatible with current embeddings.
3. Runtime includes safe fallback behavior when persisted index is stale or invalid.

**UI hint**: no

## Phase 5: Documentation Alignment

Goal: Align all top-level project docs with implemented behavior and current architecture.

Requirements: DOCS-01

Success criteria:
1. Public docs accurately describe config API surface, thresholds, and phase commands.
2. Deprecated or misleading references are removed or clearly labeled.
3. README/project guidance points to the current `.planning` artifacts and workflow entrypoints.

**UI hint**: no

---
*Last updated: 2026-04-11 after roadmap initialization*

