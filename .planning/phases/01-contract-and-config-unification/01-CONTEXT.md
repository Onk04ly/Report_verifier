# Phase 1: Contract and Config Unification - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Unify runtime configuration and claim contract behavior across verifier and extractor so thresholds/constants come from centralized config, schema is explicit, and outputs remain deterministic without compatibility ambiguity.

</domain>

<decisions>
## Implementation Decisions

### Configuration Source and Injection
- **D-01:** `ClaimExtractor` must consume centralized configuration from `get_global_config()` via a full config object contract, not inline local defaults.
- **D-02:** Missing/invalid required config must fail fast with explicit error messages and listed missing keys.
- **D-03:** All runtime scoring constants currently hardcoded in extractor logic (including distance normalization and penalty constants) move into `src/medical_config.py` in this phase.
- **D-04:** Modules use accessor-driven config usage consistently; avoid ad-hoc threshold literals in runtime code paths.
- **D-05:** Add config invariant validation (`__post_init__`) in Phase 1 to reject invalid threshold/range states.
- **D-06:** Remove inline notebook/script config override patterns where they conflict with centralized runtime contract.

### Canonical Claim Schema
- **D-07:** Canonical claim text key is `claim_text`.
- **D-08:** Schema mismatch between extractor and verifier is a hard error (no silent fallback).
- **D-09:** Validate schema at both extractor output boundary and verifier input boundary.
- **D-10:** Use strict required claim keys with typed defaults only for explicitly optional fields.

### Compatibility and Rollout
- **D-11:** No compatibility window for dual `text`/`claim_text`; update call sites atomically in Phase 1.
- **D-12:** No schema versioning field in this phase; enforce one stable schema directly.
- **D-13:** Execute as an atomic refactor across `medical_config`, `claim_extractor_fixed`, and `medical_verifier`.
- **D-14:** If downstream callers break, fix them inside Phase 1 before close.

### Scope Boundaries for Phase 1
- **D-15:** In-scope files are core runtime modules plus immediate caller files that break due to contract/config changes.
- **D-16:** Defer `claim_extractor_fixed.py` rename to later phase to avoid unrelated churn.
- **D-17:** Defer unrelated cleanup (e.g., `main_legacy`, broad tech-debt cleanup) unless it blocks phase verification.
- **D-18:** Update only behavior-impacted docs in this phase; broader doc alignment remains Phase 5.

### Regression Gate
- **D-19:** Phase completion requires runtime smoke check plus targeted schema/config verification checks.
- **D-20:** Add lightweight focused `pytest` coverage for config+schema guardrails in Phase 1.
- **D-21:** Gate command set must include `python src/medical_verifier.py` and focused contract tests.
- **D-22:** Phase does not close with failing gate checks; failures are fixed in-phase.

### the agent's Discretion
- Internal naming for new config fields can follow existing `SCREAMING_SNAKE_CASE` conventions in `ConfigurationSettings` as long as decision constraints above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` - Phase 1 section: "Contract and Config Unification"
- `.planning/REQUIREMENTS.md` - `VERI-01`, `VERI-02`, `VERI-03`
- `.planning/PROJECT.md` - Core Value, Constraints, and Active requirements

### Runtime Contract Targets
- `src/medical_config.py` - centralized thresholds/parameters and accessor API
- `src/claim_extractor_fixed.py` - current inline config defaults, scoring constants, claim payload shape
- `src/medical_verifier.py` - extractor wiring, schema fallback logic, export structure

### Codebase Guidance
- `.planning/codebase/CONVENTIONS.md` - config access and naming patterns
- `.planning/codebase/CONCERNS.md` - documented contract/config drift risks relevant to this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConfigurationSettings` + `get_*` accessor methods in `src/medical_config.py` can serve as the canonical config interface.
- `MedicalVerifier.__init__` already initializes global config and is the natural injection point for extractor contract enforcement.
- Existing verifier export flow in `export_results()` provides a stable location to confirm deterministic output shape.

### Established Patterns
- Project already uses a centralized config module pattern but extractor still carries duplicated inline defaults.
- Runtime data exchange is dict-based; schema validation wrappers must be explicit because there is no typed model layer.
- Fail-soft behavior exists in several paths; this phase intentionally shifts contract-critical paths to fail-fast.

### Integration Points
- `MedicalVerifier -> ClaimExtractor` constructor path is the primary contract seam.
- Claim payload generation in extractor feeds risk assessment and export flattening in verifier.
- Any immediate notebook/script callers depending on old keys must be updated in same phase.

</code_context>

<specifics>
## Specific Ideas

- Strong preference for strictness over transitional compatibility in this phase (all key decisions selected as strict option).
- Keep phase tightly focused on contract/config unification rather than opportunistic cleanup.

</specifics>

<deferred>
## Deferred Ideas

- `claim_extractor_fixed.py` file rename
- Legacy cleanup work not required for Phase 1 success criteria

</deferred>

---

*Phase: 01-contract-and-config-unification*
*Context gathered: 2026-04-11*

