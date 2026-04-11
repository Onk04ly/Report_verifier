# Phase 1: Contract and Config Unification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `01-CONTEXT.md`.

**Date:** 2026-04-11
**Phase:** 01-contract-and-config-unification
**Areas discussed:** Config Injection Strategy, Canonical Claim Schema, Compatibility Policy, Phase 1 Scope Tightness, Regression Gate

---

## Config Injection Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Strict centralized config contract / fail-fast / move hardcoded constants / accessor-first / invariants now | ✓ |
| 2 | Partial or compatibility-first alternatives | |
| 3 | Flexible mixed/deferred alternatives | |
| 4 | Agent discretion | |

**User choices:** Q1-Q8 all selected Option 1.
**Notes:** User preference is strict enforcement with no ambiguity and immediate centralization.

---

## Canonical Claim Schema

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | `claim_text`, fail-fast mismatches, dual-boundary validation, strict required keys | ✓ |
| 2 | Compatibility/soft-normalization alternatives | |
| 3 | Long-term dual schema support | |
| 4 | Agent discretion | |

**User choices:** Q1-Q4 all selected Option 1.
**Notes:** User accepted hard schema boundary over tolerant behavior.

---

## Compatibility Policy

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Immediate contract switch, atomic rollout, fix breakages in-phase | ✓ |
| 2 | Transitional compatibility strategies | |
| 3 | Deferred or split rollout strategies | |
| 4 | Agent discretion | |

**User choices:** Q1-Q4 all selected Option 1.
**Notes:** User requested decisive cutover with no compatibility window.

---

## Phase 1 Scope Tightness

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Runtime + immediate callers only, defer unrelated cleanup/rename, limited doc updates | ✓ |
| 2 | Narrower or deferral-heavy alternatives | |
| 3 | Broader cleanup alternatives | |
| 4 | Agent discretion | |

**User choices:** Q1-Q4 all selected Option 1.
**Notes:** User prioritized strict scope containment.

---

## Regression Gate

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | Smoke + targeted tests, pytest checks now, fail-close gate | ✓ |
| 2 | Weaker gate alternatives | |
| 3 | Overly broad or deferred alternatives | |
| 4 | Agent discretion | |

**User choices:** Q1-Q4 all selected Option 1.
**Notes:** User requires passing verification checks before phase closure.

---

## the agent's Discretion

- Minor naming and implementation details within the strict contracts selected above.

## Deferred Ideas

- Rename `claim_extractor_fixed.py` deferred.
- Unrelated legacy cleanup deferred.

