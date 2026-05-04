# Phase 6: Documentation Alignment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 06-documentation-alignment
**Areas discussed:** Doc consolidation strategy, README.md, Config API accuracy

---

## Doc Consolidation Strategy

### workflow.txt disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Rewrite to match actual 6-phase pipeline | Replace stale content with correct phase commands, file names, and structure | ✓ |
| Delete it | CLAUDE.md already has correct phase commands — a second file risks future drift | |
| Keep as-is, add a deprecation notice | Label it outdated and point to CLAUDE.md. Lowest effort | |

**User's choice:** Rewrite to match actual 6-phase pipeline
**Notes:** workflow.txt was referencing a 7-phase structure with non-existent scripts (evaluation_pipeline.py, evaluation_dashboard.ipynb) and contained garbled/duplicated text.

---

### CONFIG_INTEGRATION_GUIDE.md + IMPLEMENTATION_SUMMARY.md disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Merge into one accurate IMPLEMENTATION_SUMMARY.md | Single file with correct config API, actual thresholds, and accurate component list | ✓ |
| Update each in-place separately | Fixes both files independently — keeps narrative style but risks future drift | |
| Archive both — CLAUDE.md is sufficient | Delete or move to docs/ folder | |

**User's choice:** Merge into one accurate IMPLEMENTATION_SUMMARY.md
**Notes:** Both files had wrong accessor names (config.CONFIDENCE_HIGH vs get_confidence_thresholds()) and wrong threshold values (0.28/0.25 vs 0.30/0.22).

---

### Target tone

| Option | Description | Selected |
|--------|-------------|----------|
| Dissertation reviewer | Clear, professional, third-person. Suitable for academic submission | |
| Developer/contributor | Practical and direct. Focuses on how to run, configure, and extend | ✓ |
| General technical reader | Balanced: overview + commands + component summary | |

**User's choice:** Developer/contributor
**Notes:** Drops the first-person "I created" / "I noticed" narrative style of the old docs.

---

## README.md

### Should we write a README, and at what level?

| Option | Description | Selected |
|--------|-------------|----------|
| Write a concise project README | 1-2 page overview + pointers to SETUP_GUIDE.md and CLAUDE.md | |
| Write a full README (replace SETUP_GUIDE.md) | Put everything in README: setup, architecture, usage | ✓ |
| Leave README empty | CLAUDE.md and SETUP_GUIDE.md cover the ground | |

**User's choice:** Write a full README (replace SETUP_GUIDE.md)

---

### README sections

All four sections selected (multiselect):
- Project overview + architecture
- Setup + installation (absorbs SETUP_GUIDE.md)
- Usage / phase commands
- Configuration reference

---

### SETUP_GUIDE.md after README absorbs it

| Option | Description | Selected |
|--------|-------------|----------|
| Delete SETUP_GUIDE.md | Content moves into README. One source of truth | ✓ |
| Keep SETUP_GUIDE.md as a reference | README links to it for deeper setup details | |

**User's choice:** Delete SETUP_GUIDE.md

---

## Config API Accuracy

### How much of the config API to document

| Option | Description | Selected |
|--------|-------------|----------|
| Accessor pattern + current threshold values | Show get_global_config(), 4 accessor methods, and current values | ✓ |
| Accessor pattern only, no values | Show how to call API; tell readers to check medical_config.py for numbers | |
| Full dataclass reference | Every field, default, and preset. Comprehensive but may go stale | |

**User's choice:** Accessor pattern + current threshold values

---

### Include preset environments?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, mention all 3 presets with brief descriptions | production / development / testing — low maintenance burden | ✓ |
| No — just the default config | Simpler doc, fewer things to keep in sync | |

**User's choice:** Yes, mention all 3 presets with brief descriptions

---

## Claude's Discretion

- Exact section headings, prose wording, and ordering within README and IMPLEMENTATION_SUMMARY.md
- Whether to add a brief mention of Phase 5 new components (disease_buckets.py, disease_evaluator.py, expansion_gate.py) if it fits naturally

## Deferred Ideas

- Phase 5 component deep-dive docs (DiseaseKBBuckets, DiseaseEvaluator, ExpansionGate) — user skipped this area; deferred to potential future phase when broad multi-disease expansion is pursued
