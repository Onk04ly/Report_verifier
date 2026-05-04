# Medical AI Hallucination Detection and Verification System

## What This Is

This is a brownfield research prototype that verifies medical claims from clinical text against a PubMed-derived knowledge base. It extracts claims, retrieves supporting evidence, scores confidence, and produces risk plus safety outputs for clinician review. Current strategy is disease-specialist mode: optimize hallucination detection deeply for 2-3 diseases before broad multi-disease scaling.

## Core Value

Potentially unsafe or implausible medical claims are identified with high precision for a tightly scoped disease set (2-3 diseases), triggering explicit expert-review decisions before trust is placed in generated medical text.

## Requirements

### Validated

- ✓ End-to-end pipeline exists: PubMed fetch -> preprocess -> claim extraction -> verification -> report generation
- ✓ Structured verification exports are produced (`outputs/medical_verification.json`, `.csv`, safety log)
- ✓ Multi-layer risk assessment and responsible-AI warnings are implemented in runtime flow

### Active

*(No active requirements — all v1.0 requirements validated)*

### Validated in Phase 6 (Documentation Alignment)

- ✓ Align top-level docs with real implemented APIs, thresholds, and workflow behavior (DOCS-01)

### Out of Scope

- Immediate clinical deployment decision support - current project is a research prototype, not regulated clinical software
- Full real-time distributed serving infrastructure - current scope is local/offline dissertation execution
- Broad multi-disease verification in v1 - deferred until specialist disease performance targets are met

## Context

- Codebase is already implemented under `src/` with known architecture documentation in `.planning/codebase/`.
- Graph knowledge context exists under `graphify-out/` and identifies `ClaimExtractor` and `MedicalVerifier` as the most connected core components.
- Known concerns include missing formal tests, config drift, legacy duplicate modules, brittle safety pattern matching, and documentation mismatch with actual APIs.
- Existing artifacts and notebooks are sufficient to continue from brownfield state without rebooting project foundations.

## Constraints

- **Domain Safety**: Medical outputs must always be framed as assistive and non-diagnostic - required for research ethics and safe usage.
- **Brownfield Compatibility**: New work must preserve current pipeline outputs and file formats unless migrations are explicitly defined.
- **Reproducibility**: Thresholds, scoring behavior, and KB artifact lineage must remain auditable for dissertation review.
- **Resource Profile**: Local CPU-first execution should remain viable; avoid requiring new heavy infrastructure for v1 improvements.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Initialize as brownfield project | Existing implemented system and codebase map already available | ✓ Good |
| Use centralized config as single source of truth | Reduces drift and hidden magic numbers across modules | - Pending |
| Prioritize safety/test hardening before feature expansion | Current highest risk is reliability and validation quality, not missing UI features | - Pending |
| Prioritize specialist accuracy over broad coverage | Focus on 2-3 diseases expected to improve precision and reduce false positives/false negatives | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-04 after Phase 6 complete — all v1.0 requirements validated*

