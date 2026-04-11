# Requirements: Medical AI Hallucination Detection and Verification System

**Defined:** 2026-04-11
**Core Value:** Potentially unsafe or implausible medical claims are identified reliably enough to trigger explicit expert-review decisions before trust is placed in generated medical text.

## v1 Requirements

### Verification Core

- [ ] **VERI-01**: Runtime thresholds and retrieval/scoring parameters are sourced from centralized configuration only
- [ ] **VERI-02**: Claim extractor and verifier use one stable claim-field schema with explicit validation
- [ ] **VERI-03**: Verification output includes deterministic risk/safety structures for downstream consumers

### Safety and Guardrails

- [ ] **SAFE-01**: System detects unsafe medical guidance using hybrid rule + semantic checks, not exact keyword matching only
- [ ] **SAFE-02**: System validates input size/shape and enforces claim extraction limits from configuration
- [ ] **SAFE-03**: System marks or fails degraded mode when critical embedding models are unavailable

### Testing and Reliability

- [ ] **TEST-01**: Automated tests verify four-layer risk transitions and threshold boundaries
- [ ] **TEST-02**: Automated tests verify dangerous-term and evidence-violation detection behavior
- [ ] **TEST-03**: Automated tests cover confidence score computation and regression-sensitive constants

### Data and Operations

- [ ] **DATA-01**: KB pipeline writes reproducibility metadata (timestamp, source scope, model versions, hashes)
- [ ] **DATA-02**: Runtime persists and reuses FAISS index to reduce cold-start cost

### Documentation

- [ ] **DOCS-01**: Project docs reflect real code APIs, thresholds, and execution flow without stale claims

## v2 Requirements

### Extended Capability

- **EXT-01**: Incremental KB refresh mode without full end-to-end rebuild
- **EXT-02**: Native PDF export pipeline for reports
- **EXT-03**: Pluggable vector store backend for larger-than-local scale

## Out of Scope

| Feature | Reason |
|---------|--------|
| Clinical diagnosis automation | System is assistive verification tooling, not an autonomous clinical decision engine |
| Multi-tenant production SaaS deployment | Current milestone is research hardening in local/brownfield environment |
| Full EHR integration | External interoperability is beyond current dissertation scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VERI-01 | Phase 1 | Pending |
| VERI-02 | Phase 1 | Pending |
| VERI-03 | Phase 1 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 2 | Pending |
| SAFE-03 | Phase 2 | Pending |
| TEST-01 | Phase 3 | Pending |
| TEST-02 | Phase 3 | Pending |
| TEST-03 | Phase 3 | Pending |
| DATA-01 | Phase 4 | Pending |
| DATA-02 | Phase 4 | Pending |
| DOCS-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 after initial definition*

