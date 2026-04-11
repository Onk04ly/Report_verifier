# Phase 1: Contract and Config Unification - Research

**Researched:** 2026-04-11  
**Domain:** Python runtime contract/config refactor for medical verification pipeline  
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `ClaimExtractor` must consume centralized configuration from `get_global_config()` via a full config object contract, not inline local defaults.
- **D-02:** Missing/invalid required config must fail fast with explicit error messages and listed missing keys.
- **D-03:** All runtime scoring constants currently hardcoded in extractor logic (including distance normalization and penalty constants) move into `src/medical_config.py` in this phase.
- **D-04:** Modules use accessor-driven config usage consistently; avoid ad-hoc threshold literals in runtime code paths.
- **D-05:** Add config invariant validation (`__post_init__`) in Phase 1 to reject invalid threshold/range states.
- **D-06:** Remove inline notebook/script config override patterns where they conflict with centralized runtime contract.
- **D-07:** Canonical claim text key is `claim_text`.
- **D-08:** Schema mismatch between extractor and verifier is a hard error (no silent fallback).
- **D-09:** Validate schema at both extractor output boundary and verifier input boundary.
- **D-10:** Use strict required claim keys with typed defaults only for explicitly optional fields.
- **D-11:** No compatibility window for dual `text`/`claim_text`; update call sites atomically in Phase 1.
- **D-12:** No schema versioning field in this phase; enforce one stable schema directly.
- **D-13:** Execute as an atomic refactor across `medical_config`, `claim_extractor_fixed`, and `medical_verifier`.
- **D-14:** If downstream callers break, fix them inside Phase 1 before close.
- **D-15:** In-scope files are core runtime modules plus immediate caller files that break due to contract/config changes.
- **D-16:** Defer `claim_extractor_fixed.py` rename to later phase to avoid unrelated churn.
- **D-17:** Defer unrelated cleanup (e.g., `main_legacy`, broad tech-debt cleanup) unless it blocks phase verification.
- **D-18:** Update only behavior-impacted docs in this phase; broader doc alignment remains Phase 5.
- **D-19:** Phase completion requires runtime smoke check plus targeted schema/config verification checks.
- **D-20:** Add lightweight focused `pytest` coverage for config+schema guardrails in Phase 1.
- **D-21:** Gate command set must include `python src/medical_verifier.py` and focused contract tests.
- **D-22:** Phase does not close with failing gate checks; failures are fixed in-phase.

### Claude's Discretion
- Internal naming for new config fields can follow existing `SCREAMING_SNAKE_CASE` conventions in `ConfigurationSettings` as long as decision constraints above are preserved.

### Deferred Ideas (OUT OF SCOPE)
- `claim_extractor_fixed.py` file rename
- Legacy cleanup work not required for Phase 1 success criteria
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VERI-01 | Runtime thresholds and retrieval/scoring parameters are sourced from centralized configuration only | Existing config surface is in `src/medical_config.py`; extractor still has inline defaults and hardcoded scoring constants that must move there. |
| VERI-02 | Claim extractor and verifier use one stable claim-field schema with explicit validation | `MedicalVerifier` currently reads `claim['text']` in export and risk paths while phase decisions require canonical `claim_text` and hard failures on schema drift. |
| VERI-03 | Verification output includes deterministic risk/safety structures for downstream consumers | `MedicalVerifier.export_results()` already emits JSON/CSV plus safety log, but current result shape mixes claim fields and fallback logic; deterministic boundary validation is needed. |
</phase_requirements>

## Summary

Phase 1 is a contract-hardening refactor, not a feature expansion. The current codebase already has a centralized config module, but `ClaimExtractor` still constructs its own inline default config dict and the verifier passes only a partial threshold dict into it. That means the extractor does not actually consume the full canonical config object, and several runtime scoring constants remain embedded in extractor logic instead of flowing through `src/medical_config.py` [VERIFIED: `src/claim_extractor_fixed.py`, `src/medical_config.py`, `src/medical_verifier.py`].

The claim schema is also not stable today. The extractor emits `text` for each claim, while the verifier’s CSV export and risk assessment logic still reference `claim['text']` with only an implicit fallback in one place. Phase 1 should make `claim_text` the only accepted canonical field, validate it at both the extractor boundary and verifier boundary, and fail fast when callers send the old shape [VERIFIED: `CONTEXT.md`, `src/claim_extractor_fixed.py`, `src/medical_verifier.py`].

**Primary recommendation:** centralize all extractor tunables in `src/medical_config.py`, change constructor wiring so `ClaimExtractor` receives the full config contract, add strict schema validation for `claim_text`, and gate the change with a smoke run of `python src/medical_verifier.py` plus focused contract tests.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13.11150.1013 on this machine; project target is 3.8+ [VERIFIED: shell, `requirements.txt`] | Runtime | Repository is Python-first and all core modules are Python scripts. |
| pandas | `>=1.5.0` [VERIFIED: `requirements.txt`] | CSV/table I/O | Existing verifier and extractor already use DataFrames and CSV exports. |
| numpy | `>=1.21.0` [VERIFIED: `requirements.txt`] | Numerical arrays | Needed for embedding handling and deterministic numeric scoring. |
| scikit-learn | `>=1.1.0` [VERIFIED: `requirements.txt`] | Cosine similarity and fallback vectorization | Already used in confidence scoring and should remain the standard similarity helper. |
| spacy | `>=3.4.0` [VERIFIED: `requirements.txt`] | Sentence splitting and biomedical NLP | Existing extractor logic depends on spaCy sentence segmentation and NER. |
| faiss-cpu | `>=1.7.0` [VERIFIED: `requirements.txt`] | ANN retrieval over KB embeddings | The retriever is built on FAISS and is the runtime retrieval mechanism. |
| torch | `>=1.12.0` [VERIFIED: `requirements.txt`] | Transformer inference backend | Required by the Bio_ClinicalBERT embedding path already used in extraction. |
| transformers | `>=4.20.0` [VERIFIED: `requirements.txt`] | Hugging Face model loading | Current embedding path loads Bio_ClinicalBERT via transformers. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sentence-transformers | `>=2.2.0` [VERIFIED: `requirements.txt`] | Sentence embedding utilities | Only if the implementation adds sentence-level embedding helpers beyond the current extractor. |
| scispacy | `>=0.5.0` [VERIFIED: `requirements.txt`] | Biomedical spaCy integration | Use for the installed medical models required by the extractor. |
| requests | `>=2.28.0` [VERIFIED: `requirements.txt`] | PubMed/NCBI HTTP client | Keep for fetch pipeline, not Phase 1 contract work. |
| pytest | not declared in `requirements.txt`; not installed locally [VERIFIED: shell, `requirements.txt`] | Contract/regression tests | Needed for the new focused config/schema guards. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline extractor defaults | Centralized `ConfigurationSettings` accessors | Inline defaults create contract drift and make enforcement impossible. |
| Loose schema fallback (`text` or `claim_text`) | Strict `claim_text` only | Fallback masks caller bugs and conflicts with the no-transition decision. |
| Silent coercion of invalid config | `__post_init__` validation with explicit errors | Coercion hides bad state and makes runtime behavior non-auditable. |

**Installation:**
```bash
pip install -r requirements.txt
```

## Architecture Patterns

### Recommended Project Structure
```text
src/
├── medical_config.py        # single source of truth for runtime tunables and validation
├── claim_extractor_fixed.py # claim extraction, retrieval, confidence scoring, schema emission
└── medical_verifier.py      # verification orchestration, schema validation, exports
```

### Pattern 1: Full Config Injection
**What:** Pass the complete centralized config object into runtime components, and make component code read named accessors/fields from that object instead of ad-hoc literals [VERIFIED: `src/medical_config.py`, `src/medical_verifier.py`, `CONTEXT.md`].  
**When to use:** Any runtime path that affects extraction, scoring, thresholds, safety, or output shape.  
**Example:**
```python
# Source: `src/medical_config.py`, `src/medical_verifier.py`
config = get_global_config()
extractor = ClaimExtractor(config=config)
thresholds = config.get_confidence_thresholds()
weights = config.get_evidence_weights()
```

### Pattern 2: Boundary Schema Validation
**What:** Validate the claim payload when it leaves the extractor and again when the verifier consumes it; reject missing required keys immediately [VERIFIED: `CONTEXT.md`, `src/medical_verifier.py`].  
**When to use:** Every place that accepts claim dicts or emits downstream result objects.  
**Example:**
```python
# Source: inferred from `CONTEXT.md` decisions and current dict-based runtime flow
required_keys = {"claim_text", "verification_confidence", "verification_score"}
missing = required_keys - set(claim.keys())
if missing:
    raise ValueError(f"Invalid claim schema, missing keys: {sorted(missing)}")
```

### Pattern 3: Deterministic Export Shape
**What:** Keep JSON/CSV export keys stable, ordered, and derived from one canonical result shape so downstream consumers do not need schema guesses [VERIFIED: `src/medical_verifier.py`].  
**When to use:** Any report or batch export generated from verification results.  
**Example:**
```python
# Source: `src/medical_verifier.py`
export_data = {
    "metadata": {...},
    "verification_results": results,
    "global_safety_summary": self._generate_global_safety_summary(results),
}
```

### Anti-Patterns to Avoid
- **Inline config literals in runtime paths:** they recreate the drift this phase is meant to remove.
- **Silent schema fallback between `text` and `claim_text`:** it hides invalid callers and violates the strict compatibility decision.
- **Ad-hoc normalization of invalid thresholds:** validation should fail fast instead of producing undefined scoring behavior.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Threshold and scoring storage | Per-class default dicts and literal constants | `ConfigurationSettings` in `src/medical_config.py` | There is already a central config object and accessor API. |
| Claim schema tolerance | Manual `if text else claim_text` compatibility logic | Strict required-key validation | Dual-shape support would prolong drift and conflict with the phase decision. |
| Export safety shape | Custom downstream parsing conventions | Stable JSON/CSV export contracts from verifier | Export consumers should depend on one stable schema, not inferred structure. |

**Key insight:** the hard part is not calculating thresholds; it is preventing the extractor, verifier, and export layer from each inventing their own version of the contract.

## Common Pitfalls

### Pitfall 1: Partial Config Injection
**What goes wrong:** Passing only a subset of config values to `ClaimExtractor` leaves hidden defaults in place and makes phase 1 look complete while the runtime still diverges [VERIFIED: `src/medical_verifier.py`, `src/claim_extractor_fixed.py`].  
**Why it happens:** The verifier currently passes `get_confidence_thresholds()` only, while the extractor still seeds its own default dict.  
**How to avoid:** Pass the full config object, and remove any runtime branch that falls back to inline defaults for extractor tunables.  
**Warning signs:** `self.config = config or {...}` remains in extraction code; threshold names appear in more than one module.

### Pitfall 2: Schema Drift Hidden by Fallbacks
**What goes wrong:** One module emits `text` while another expects `claim_text`, and the code “works” until a downstream path breaks or silently skips a field [VERIFIED: `src/claim_extractor_fixed.py`, `src/medical_verifier.py`, `CONTEXT.md`].  
**Why it happens:** Dict-based pipelines make it easy to accept multiple names temporarily.  
**How to avoid:** Validate required keys at both boundaries and raise a hard error on mismatch.  
**Warning signs:** Any branch that says “fallback”, “default to text”, or “claim_text if present else text”.

### Pitfall 3: Hidden Scoring Constants
**What goes wrong:** A score changes because of an untracked literal in the extractor instead of a config change, breaking reproducibility and auditability [VERIFIED: `src/claim_extractor_fixed.py`].  
**Why it happens:** The implementation currently hardcodes distance normalization and penalty values inside confidence computation.  
**How to avoid:** Move all runtime tunables into `src/medical_config.py`, and read them through accessors.  
**Warning signs:** Values like `100`, `35.0`, `0.2`, `0.4`, or `0.7` appear inside scoring logic rather than config.

## Code Examples

Verified patterns from current code and phase decisions:

### Central Config Access
```python
# Source: `src/medical_config.py`
config = get_global_config()
thresholds = config.get_confidence_thresholds()
safety = config.get_safety_config()
risks = config.get_risk_thresholds()
weights = config.get_evidence_weights()
params = config.get_extraction_params()
```

### Deterministic Export Skeleton
```python
# Source: `src/medical_verifier.py`
export_data = {
    "metadata": {
        "export_timestamp": datetime.now().isoformat(),
        "safety_compliance": "Healthcare AI Safety Standards",
        "disclaimer": "FOR QUALITY ASSURANCE USE ONLY - NOT FOR DIRECT CLINICAL DECISIONS",
    },
    "verification_results": results,
    "global_safety_summary": self._generate_global_safety_summary(results),
}
```

### Strict Schema Check
```python
# Source: inferred from `CONTEXT.md` decisions and current dict-based flow
required = {"claim_text", "verification_confidence", "verification_score", "medical_entities"}
missing = required - set(claim.keys())
if missing:
    raise ValueError(f"Claim schema mismatch: missing {sorted(missing)}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline per-class defaults in runtime code | Centralized config object with accessors | Already partially adopted in repo [VERIFIED: `src/medical_config.py`] | Phase 1 must finish the migration and eliminate leftovers. |
| Soft schema fallback | Strict required-key validation | Decision locked in Phase 1 [VERIFIED: `CONTEXT.md`] | Fewer silent failures; more explicit caller fixes. |
| Implicit export shape | Deterministic JSON/CSV result shape with safety log | Already present in `export_results()` [VERIFIED: `src/medical_verifier.py`] | Phase 1 should normalize the claim fields feeding export. |

**Deprecated/outdated:**
- Mixed claim field naming (`text` vs `claim_text`) should be treated as invalid in this phase [VERIFIED: `CONTEXT.md`].
- Constructor-local extraction defaults should be removed from the runtime contract [VERIFIED: `src/claim_extractor_fixed.py`, `CONTEXT.md`].

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research. The planner and discuss-phase use this section to identify decisions that need user confirmation before execution.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | None. | N/A | N/A |

**If this table is empty:** All claims in this research were verified or cited - no user confirmation needed.

## Open Questions

1. **Should `ConfigurationSettings` gain validation-only helpers or a full `__post_init__` contract?**
   - What we know: Phase decisions require invariant validation and fail-fast behavior [VERIFIED: `CONTEXT.md`].
   - What’s unclear: Whether validation should be pure `__post_init__` or also exposed as a reusable method for tests and future phases.
   - Recommendation: implement `__post_init__` now, and keep validation logic factored so tests can call the same checks directly.

2. **Where should the canonical claim schema be defined for the phase?**
   - What we know: current runtime is dict-based, and the phase explicitly forbids schema versioning and compatibility windows [VERIFIED: `CONTEXT.md`].
   - What’s unclear: whether the schema should live in `medical_verifier.py`, `claim_extractor_fixed.py`, or a small shared helper module.
   - Recommendation: keep it in a small shared helper only if it does not broaden phase scope; otherwise duplicate the same validation shape at both boundaries as the decision requires.

3. **What test framework is available for Phase 1 verification?**
   - What we know: no project test files or pytest config were found, and `pytest` is not installed locally [VERIFIED: shell, repo scan].
   - What’s unclear: whether the team prefers to add a lightweight `tests/` package now or keep validation as a temporary smoke-only gate.
   - Recommendation: add a minimal `tests/test_contracts.py` in this phase because D-20/D-21 require targeted contract tests.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Runtime execution | ✓ | 3.13.11150.1013 | Project target still supports 3.8+ [VERIFIED: shell, `requirements.txt`] |
| pip | Dependency install | ✓ | bundled with Python 3.13 | `python -m pip` |
| pytest | Focused contract tests | ✗ | - | Add pytest to dev setup; until then use only manual smoke checks |

**Missing dependencies with no fallback:**
- None that block the phase entirely, but contract-test automation is currently unavailable until `pytest` is installed.

**Missing dependencies with fallback:**
- `pytest` - fall back to manual smoke validation temporarily, but Phase 1 should add the test dependency because the phase decisions require targeted contract tests.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (not currently installed locally) |
| Config file | none found |
| Quick run command | `python src/medical_verifier.py` |
| Full suite command | `pytest tests/test_contracts.py -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VERI-01 | Extractor uses centralized config only; no inline runtime defaults or hardcoded scoring literals | unit/contract | `pytest tests/test_contracts.py::test_extractor_reads_global_config -x` | ❌ Wave 0 |
| VERI-02 | Claim schema must require `claim_text` at extractor and verifier boundaries | unit/contract | `pytest tests/test_contracts.py::test_claim_schema_requires_claim_text -x` | ❌ Wave 0 |
| VERI-03 | Exported verification output remains deterministic and structurally stable | integration/contract | `pytest tests/test_contracts.py::test_export_shape_is_deterministic -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python src/medical_verifier.py`
- **Per wave merge:** `pytest tests/test_contracts.py -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- `tests/` package - missing, needed for Phase 1 contract tests.
- `tests/test_contracts.py` - missing, needed to pin config/schema/export behavior.
- `pytest` dependency - missing from the local environment and from `requirements.txt`.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Not in scope for this local research prototype. |
| V3 Session Management | no | Not in scope for this local research prototype. |
| V4 Access Control | no | Not part of this phase’s runtime contract work. |
| V5 Input Validation | yes | Strict schema validation for `claim_text` and required claim keys. |
| V6 Cryptography | no | No cryptographic work is in scope for Phase 1. |

### Known Threat Patterns for Python dict-based runtime contracts

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Schema spoofing / missing required keys | Tampering | Validate required keys and raise on mismatch. |
| Unsafe default thresholds | Tampering | Centralize tunables and reject invalid ranges in config validation. |
| Silent export drift | Repudiation | Produce deterministic result shapes and safety logs. |

## Sources

### Primary (HIGH confidence)
- [`src/medical_config.py`] - current centralized configuration surface and accessor methods.
- [`src/claim_extractor_fixed.py`] - inline defaults, hardcoded scoring constants, and emitted claim shape.
- [`src/medical_verifier.py`] - config injection path, schema assumptions, and export structure.
- [`.planning/phases/01-contract-and-config-unification/01-CONTEXT.md`] - locked phase decisions and scope.
- [`.planning/REQUIREMENTS.md`] - VERI-01, VERI-02, VERI-03 definitions.
- [`.planning/ROADMAP.md`] - Phase 1 success criteria and gate expectations.
- [`CLAUDE.md`] - project workflow and environment constraints.
- [`requirements.txt`] - declared project dependencies.

### Secondary (MEDIUM confidence)
- None used.

### Tertiary (LOW confidence)
- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - grounded in repo requirements and current code, but package versions were not registry-verified.
- Architecture: HIGH - directly supported by current source and locked phase decisions.
- Pitfalls: HIGH - directly observed in runtime code and context decisions.

**Research date:** 2026-04-11  
**Valid until:** 2026-05-11
