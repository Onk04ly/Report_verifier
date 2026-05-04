# Phase 6: Documentation Alignment - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Align all top-level project docs with implemented behavior and current architecture. Eliminate stale APIs, wrong thresholds, broken phase commands, and duplicated content. End state: a developer/contributor can orient from README.md alone; workflow.txt gives accurate execution commands; IMPLEMENTATION_SUMMARY.md has the correct config API.

</domain>

<decisions>
## Implementation Decisions

### D-01: workflow.txt
- **Rewrite** workflow.txt to match the actual 6-phase pipeline.
- Replace stale 7-phase structure, non-existent script references (`evaluation_pipeline.py`, `evaluation_dashboard.ipynb`), and garbled/duplicated text with correct phase commands, output file names, and phase goals matching CLAUDE.md.

### D-02: CONFIG_INTEGRATION_GUIDE.md + IMPLEMENTATION_SUMMARY.md
- **Merge** both files into a single accurate `IMPLEMENTATION_SUMMARY.md`.
- Delete `CONFIG_INTEGRATION_GUIDE.md` after content is absorbed.
- The merged doc covers: config API, actual threshold values, component overview, and preset environments. No duplication between the two files.

### D-03: Target tone
- **Developer/contributor** — practical and direct. Focus on how to run, configure, and understand component relationships. Not academic narrative style.

### D-04: README.md
- **Write a full README.md** that replaces `SETUP_GUIDE.md`.
- Sections to include:
  1. Project overview + architecture (what the system does, pipeline flow, key components)
  2. Setup + installation (absorb SETUP_GUIDE.md: pip install, SpaCy models, env vars)
  3. Usage / phase commands (how to run each phase step-by-step)
  4. Configuration reference (key thresholds, config API, how to tune — points to `src/medical_config.py`)
- **Delete SETUP_GUIDE.md** after content is absorbed into README.

### D-05: Config API documentation depth
- Show **accessor pattern + current threshold values** — enough for a contributor to use the API correctly.
- Document: `get_global_config()`, and the 4 accessor methods (`get_confidence_thresholds()`, `get_safety_config()`, `get_risk_thresholds()`, `get_evidence_weights()`).
- Include current values: `HIGH_CONFIDENCE_THRESHOLD = 0.30`, `MEDIUM_CONFIDENCE_THRESHOLD = 0.22`, `HIGH_RISK_LOW_CONF_RATIO = 0.50`, `top_k_facts = 5`.
- **Include all 3 preset environments** (production / development / testing) with brief descriptions of when to use each.

### Agent Discretion
- Exact section headings, prose wording, and ordering within README and IMPLEMENTATION_SUMMARY.md are at agent discretion — match developer/contributor tone throughout.
- If `SETUP_GUIDE.md` contains any setup detail not yet in CLAUDE.md, absorb it into README before deleting.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` — Phase 6 section: "Documentation Alignment"
- `.planning/REQUIREMENTS.md` — `DOCS-01`
- `.planning/PROJECT.md` — Core Value, Constraints

### Ground-Truth Source Files (what docs must reflect)
- `src/medical_config.py` — actual threshold values, dataclass fields, accessor methods, preset environments
- `CLAUDE.md` — correct phase commands, architecture overview, key data files (use as the accuracy reference)
- `.planning/codebase/ARCHITECTURE.md` — pipeline flow and component roles
- `src/medical_verifier.py` — risk layer structure, disease-specific pattern methods
- `src/claim_extractor_fixed.py` — FAISS retrieval, embedding logic, `disease_bucket_indices` parameter

### Stale Docs to Fix/Remove
- `workflow.txt` — rewrite (currently describes wrong 7-phase structure)
- `CONFIG_INTEGRATION_GUIDE.md` — merge into IMPLEMENTATION_SUMMARY.md, then delete
- `IMPLEMENTATION_SUMMARY.md` — rewrite as the merged accurate version
- `SETUP_GUIDE.md` — absorb into README.md, then delete
- `README.md` — write from scratch (currently empty)

### Codebase Guidance
- `.planning/codebase/CONCERNS.md` — known risks (avoid re-introducing stale claims it flags)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/medical_config.py` — `MedicalVerificationConfig` dataclass with `get_global_config()` singleton, 4 accessor methods, and preset class methods (`.production()`, `.development()`, `.testing()`). This is the authoritative source for all threshold values.
- `CLAUDE.md` — already accurate phase commands and architecture; docs should match it, not contradict it.

### Established Patterns
- Config access pattern: `cfg = get_global_config(); thresholds = cfg.get_confidence_thresholds()` — docs must show this, not direct attribute access.
- Phase 5 added new components (`src/disease_buckets.py`, `src/disease_evaluator.py`, `src/expansion_gate.py`) — these are mentioned in CLAUDE.md architecture but absent from top-level docs (user chose not to expand their coverage in Phase 6 docs; agent discretion on whether a brief mention fits).

### Integration Points
- README.md will be the primary entry point for the repo — it must reference CLAUDE.md for developer deep-dives rather than duplicating everything.

</code_context>

<specifics>
## Specific Ideas

- workflow.txt rewrite should use simple `python src/` commands (matching CLAUDE.md style), not the old `conda run -p` format that referenced a non-existent conda env path.
- IMPLEMENTATION_SUMMARY.md should be written in first-person removed / third-person style (developer/contributor tone), dropping the old "I created" / "I noticed" narrative.

</specifics>

<deferred>
## Deferred Ideas

- Phase 5 components (disease_buckets.py, disease_evaluator.py, expansion_gate.py) deep-dive documentation — user chose not to add detailed coverage of these in top-level docs during this discussion. If expansion to broad multi-disease mode proceeds, dedicated docs for these components would be appropriate then.

</deferred>

---

*Phase: 6-Documentation-Alignment*
*Context gathered: 2026-05-04*
