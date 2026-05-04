# Phase 6: Documentation Alignment - Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 5 (README.md new, workflow.txt rewrite, IMPLEMENTATION_SUMMARY.md rewrite, CONFIG_INTEGRATION_GUIDE.md delete, SETUP_GUIDE.md delete)
**Analogs found:** 4 / 5 (CONFIG_INTEGRATION_GUIDE.md and SETUP_GUIDE.md are sources to be absorbed and then deleted, not written)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `README.md` | project entrypoint doc | N/A (static doc) | `CLAUDE.md` + `SETUP_GUIDE.md` (absorb) | exact content source |
| `workflow.txt` | phase execution guide | N/A (static doc) | `CLAUDE.md` Workflow section | exact content source |
| `IMPLEMENTATION_SUMMARY.md` | architecture + config reference | N/A (static doc) | `.planning/codebase/ARCHITECTURE.md` + `src/medical_config.py` | exact content source |
| `CONFIG_INTEGRATION_GUIDE.md` | DELETE after merge | — | merged into IMPLEMENTATION_SUMMARY.md | source only |
| `SETUP_GUIDE.md` | DELETE after merge | — | merged into README.md | source only |

---

## Pattern Assignments

### `README.md` (new, project entrypoint — absorbs SETUP_GUIDE.md)

**Primary analog:** `CLAUDE.md` (accurate overview, phase commands, architecture, key data files)
**Secondary source:** `SETUP_GUIDE.md` (setup steps to absorb before deletion)

**Accurate project description** (from `CLAUDE.md` lines 7-8):
```
Medical AI Hallucination Detection and Verification System — a dissertation research project.
It analyzes medical texts to extract claims, verify them against a PubMed-sourced knowledge
base, detect implausibilities/hallucinations, and produce risk-assessed reports.
```

**Accurate data pipeline flow** (from `CLAUDE.md` lines 49-57):
```
PubMed API
  → pubmed_fetcher.py          (rate-limited fetching, 500+ articles)
  → medical_preprocessor.py   (abbreviation expansion, entity extraction, SciBERT embeddings, quality grading)
  → claim_extractor_fixed.py  (FAISS index over KB embeddings, Bio_ClinicalBERT claim embeddings, similarity scoring)
  → medical_verifier.py       (4-layer risk assessment + Responsible AI layer)
  → report_generator.py       (HTML/PDF output)
```

**Accurate phase commands** (from `CLAUDE.md` lines 24-43 — use these verbatim; do NOT use conda run format from old workflow.txt):
```bash
# Phase 1 — Fetch PubMed data → data/knowledge_base.csv
python src/pubmed_fetcher.py

# Phase 2 — Preprocess KB + generate SciBERT embeddings → data/*_preprocessed.csv, data/kb_embeddings_preprocessed.npy
python src/medical_preprocessor.py

# Phase 3 — Test claim extraction and verification engine
python src/claim_extractor_fixed.py

# Phase 4 — Run full verification pipeline → outputs/*.json, outputs/*.csv
python src/medical_verifier.py

# Phase 5 — Interactive analysis
jupyter notebook medical_verification_dashboard.ipynb

# Phase 6 — Generate HTML/PDF report
python src/report_generator.py
```

**Accurate setup commands to absorb from `SETUP_GUIDE.md`** (lines 19-37 — these are correct; absorb into README before deleting SETUP_GUIDE.md):
```bash
pip install -r requirements.txt

# Install medical entity recognition model
python -m spacy download en_ner_bc5cdr_md

# Alternative installation via URL (if above fails):
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz

# Install scientific text processing models
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
```

**Prerequisites to absorb from `SETUP_GUIDE.md`** (lines 8-12 — correct, absorb):
```
- Python 3.8 or higher
- pip package manager
- At least 8GB RAM (16GB recommended)
- Internet connection for model downloads
```

**Environment variable to include** (from `CLAUDE.md` line 82):
```
NCBI_API_KEY — set for 10 req/s rate limit instead of 3 req/s (Phase 1 only)
```

**Key data files table** (from `CLAUDE.md` lines 84-90 — accurate):
```
data/expanded_knowledge_base_preprocessed.csv  — Primary KB used at runtime
data/kb_embeddings_preprocessed.npy            — Pre-computed SciBERT embeddings; regenerating is slow
outputs/medical_verification.json              — Structured verification results
```

**Troubleshooting section to absorb from `SETUP_GUIDE.md`** (lines 120-148 — content is valid; preserve the 4 common issues: SpaCy model download, memory, FAISS, and transformer caching):
- SpaCy model download fails → use direct URL form
- Memory issues → 16GB RAM recommended
- FAISS installation issues → use `faiss-cpu` for CPU-only systems
- Transformers model loading slow → models download on first use, cache directory setup

**README must NOT include:**
- The `from medical_config import config` direct import pattern (stale; use `get_global_config()` accessor)
- Any threshold values that differ from `src/medical_config.py`: correct values are `CONFIDENCE_HIGH=0.30`, `CONFIDENCE_MEDIUM=0.22` (not 0.28/0.25 as in old docs)
- Reference to `evaluation_pipeline.py`, `evaluation_dashboard.ipynb`, or any 7-phase structure
- `conda run -p` command format
- `MedicalVerificationConfig.production()` / `.development()` / `.testing()` — these class methods do not exist
- `config_environment` parameter on `MedicalVerifier.__init__()` — does not exist

**README should reference (not duplicate):**
- `CLAUDE.md` for developer deep-dives
- `src/medical_config.py` for all threshold tuning

---

### `workflow.txt` (rewrite — currently stale with 7-phase structure and conda commands)

**Analog:** `CLAUDE.md` Workflow section (lines 22-43) — this is the authoritative phase structure.

**What to replace:** The entire content of `workflow.txt` (123 lines) which contains:
- Wrong 7-phase label on Phase 6 (large-scale evaluation, not report generation)
- Non-existent scripts: `evaluation_pipeline.py`, `evaluation_dashboard.ipynb`, `evaluation_report_generator.py`
- Garbled/duplicated text blocks (file has "Updated Phase 5 Description:y phases from start to finish:")
- All commands use `C:/Anaconda3/Scripts/conda.exe run -p c:\Report_verifier\.conda` prefix — no conda env at this path
- "Phase 7: Responsible AI Layer" described as separate phase — it is integrated into `medical_verifier.py`

**Replacement content must use:**
- Simple `python src/` commands matching CLAUDE.md style exactly
- 6-phase structure (not 7): Phase 1 through Phase 6 as defined in ROADMAP.md
- Output artifact names from actual codebase (e.g., `data/expanded_knowledge_base.csv` for Phase 1 raw output, `data/expanded_knowledge_base_preprocessed.csv` + `data/kb_embeddings_preprocessed.npy` for Phase 2)
- Phase goals matching ARCHITECTURE.md layer descriptions (lines 18-47)

**Correct 6-phase structure** (derive from CLAUDE.md workflow + ARCHITECTURE.md):
```
Phase 1 — Data Collection
  Command: python src/pubmed_fetcher.py
  Output: data/expanded_knowledge_base.csv (raw KB, 500+ articles)

Phase 2 — KB Preprocessing + Embedding
  Command: python src/medical_preprocessor.py
  Output: data/expanded_knowledge_base_preprocessed.csv, data/kb_embeddings_preprocessed.npy

Phase 3 — Claim Extraction (test/dev)
  Command: python src/claim_extractor_fixed.py
  Output: tests claim extraction and verification engine in isolation

Phase 4 — Full Verification Pipeline
  Command: python src/medical_verifier.py
  Output: outputs/medical_verification.json, outputs/medical_verification.csv,
          outputs/medical_verification_safety_log.json

Phase 5 — Interactive Analysis
  Command: jupyter notebook medical_verification_dashboard.ipynb
  Output: interactive claim/risk visualization

Phase 6 — Report Generation
  Command: python src/report_generator.py
  Output: HTML report from outputs/medical_verification.json
```

**Note on Responsible AI layer:** It is integrated into Phase 4 (`medical_verifier.py`), not a separate phase. A brief inline note is appropriate in Phase 4's description.

---

### `IMPLEMENTATION_SUMMARY.md` (rewrite — merge of IMPLEMENTATION_SUMMARY.md + CONFIG_INTEGRATION_GUIDE.md)

**Primary analog:** `src/medical_config.py` (the ground truth for API surface and values)
**Secondary analog:** `.planning/codebase/ARCHITECTURE.md` (component overview and communication table)

**Tone correction:** Current files use first-person ("I created", "I noticed", "For my dissertation project"). Rewrite in third-person developer/contributor style per D-03 and the specifics section.

**Accurate config class name** (from `src/medical_config.py` line 23):
The class is `ConfigurationSettings`, not `MedicalVerificationConfig`. The module exports a singleton named `config` and a factory function `get_global_config()`.

**Correct import pattern** (from `src/medical_config.py` lines 12-14):
```python
from medical_config import get_global_config

config = get_global_config()
thresholds = config.get_confidence_thresholds()
params = config.get_extraction_params()
```

**Do NOT document** (stale APIs in old docs that do not exist):
- `MedicalVerificationConfig.production()`, `.development()`, `.testing()` — no such class or class methods
- `config_environment` constructor parameter on `MedicalVerifier` — does not exist
- `get_global_config(custom_config_path=...)` — the actual function takes no arguments
- `switch_to_testing_environment()`, `use_development_config()`, `verify_configuration_consistency()` — none of these exist
- `config.print_config()` called to "display settings" in a notebook — `print_config()` exists but emits to stdout; note accurately

**Correct threshold values** (from `src/medical_config.py` lines 35-77 — use these, NOT the 0.28/0.25 values in old docs):
```python
CONFIDENCE_HIGH: float = 0.30       # Claims above this = HIGH confidence
CONFIDENCE_MEDIUM: float = 0.22     # Claims above this = MEDIUM confidence

HIGH_RISK_LOW_CONF_RATIO: float = 0.50   # 50%+ low confidence = HIGH RISK
MEDIUM_RISK_LOW_CONF_RATIO: float = 0.30
LOW_RISK_HIGH_CONF_RATIO: float = 0.40

TOP_K_FACTS: int = 5
MIN_SENTENCE_LENGTH: int = 8
```

**All 7 accessor methods** (from `src/medical_config.py` lines 329-407):
```python
config.get_confidence_thresholds()  # → {'high': 0.30, 'medium': 0.22}
config.get_safety_config()          # → {'high_risk_threshold': 0.30, 'critical_threshold': 0.50, ...}
config.get_risk_thresholds()        # → {'high_risk_low_conf_ratio': 0.50, ...}
config.get_evidence_weights()       # → {'similarity_avg': 0.40, 'similarity_max': 0.20, 'distance': 0.20, 'evidence_quality': 0.20}
config.get_extraction_params()      # → {'top_k_facts': 5, 'confidence_facts_count': 3, 'min_sentence_length': 8, 'max_claims_per_summary': 50}
config.get_disease_config()         # → Phase 5 disease specialization config
config.get_outlier_params()         # → distance normalization and outlier penalty params
```

**Preset environments:** There are no class methods `.production()`, `.development()`, `.testing()`. The actual approach is: edit field values directly in `ConfigurationSettings` or override after import. Document accurately — do not fabricate presets.

**Component integration pattern** (from `src/medical_config.py` docstring, lines 1-16, and ARCHITECTURE.md line 170):
```python
# Correct import used by all modules:
from medical_config import get_global_config

# In MedicalVerifier.__init__():
self.config = get_global_config()
self.confidence_thresholds = self.config.get_confidence_thresholds()
self.safety_config = self.config.get_safety_config()

# In ClaimExtractor.__init__():
self.config = get_global_config()
self.thresholds = self.config.get_confidence_thresholds()
```

**Component overview** (from ARCHITECTURE.md lines 126-158 — use as source for accurate descriptions):
- `ConfigurationSettings` (`src/medical_config.py`) — `@dataclass` singleton; validated at construction; `get_global_config()` returns the module-level instance
- `ClaimExtractor` (`src/claim_extractor_fixed.py`) — FAISS retrieval over KB; Bio_ClinicalBERT embeddings; 25+ regex claim patterns; 10 claim types; 5 ensemble plausibility penalty checks
- `MedicalVerifier` (`src/medical_verifier.py`) — orchestrates ClaimExtractor; 4-layer risk model; Responsible AI layer
- `MedicalPreprocessor` (`src/medical_preprocessor.py`) — offline-only KB preprocessing; not called at runtime
- `MedicalReportGenerator` (`src/report_generator.py`) — reads `outputs/medical_verification.json`; produces self-contained HTML

**Component communication table** (from ARCHITECTURE.md lines 163-171):
```
pubmed_fetcher.py       → medical_preprocessor.py      via file: data/expanded_knowledge_base.csv
medical_preprocessor.py → claim_extractor_fixed.py     via files: *_preprocessed.csv + .npy
claim_extractor_fixed.py → medical_verifier.py         via direct instantiation
medical_verifier.py     → report_generator.py          via file: outputs/medical_verification.json
medical_config.py       → all other modules            via module-level singleton
```

**4-layer risk model** (from ARCHITECTURE.md lines 78-101 — accurate summary):
```
Layer 1 — Medical Plausibility (highest priority)
  Detects: physiological impossibilities, patient safety risks, evidence contradictions, logical inconsistency
  Triggers CRITICAL_RISK on any CRITICAL severity issue

Layer 2 — Severity Count
  Triggers HIGH_RISK if combined HIGH-severity issues >= 2

Layer 3 — Implausibility Presence
  Any implausibility issue present → HIGH_RISK

Layer 4 — Confidence Ratio (default path)
  low_conf_ratio >= 0.50  → HIGH_RISK
  low_conf_ratio >= 0.30  → MEDIUM_RISK
  high_conf_ratio >= 0.40 → LOW_RISK
  Otherwise               → MEDIUM_RISK
```

**Phase 5 components — brief mention only** (per CONTEXT.md deferred section; user chose not to add detailed coverage):
- `src/disease_buckets.py` — disease-specific KB buckets via centroid computation
- `src/disease_evaluator.py` — per-disease precision/accuracy evaluation
- `src/expansion_gate.py` — gates broad multi-disease expansion until specialist metrics pass

**Validation behavior** (from `src/medical_config.py` lines 175-324 — this IS implemented, unlike what old docs claimed):
- `ConfigurationSettings.__post_init__()` validates all fields at construction time
- Checks: probability range [0.0, 1.0], positive integers, `CONFIDENCE_HIGH > CONFIDENCE_MEDIUM`, evidence weights sum to 1.0, dataset split fractions sum to 1.0
- Raises `ValueError` with complete diagnostic listing all invalid fields

---

## Shared Patterns

### Accurate Phase Command Format
**Source:** `CLAUDE.md` lines 24-43
**Apply to:** `README.md` (usage section), `workflow.txt` (all commands)
```bash
python src/<script_name>.py
jupyter notebook <notebook_name>.ipynb
```
Never use `conda run -p ...` format. Never reference `evaluation_pipeline.py`, `evaluation_dashboard.ipynb`, or `evaluation_report_generator.py` — these scripts do not exist.

### Accurate Config Import Pattern
**Source:** `src/medical_config.py` lines 12-14
**Apply to:** `README.md` (config reference section), `IMPLEMENTATION_SUMMARY.md` (all code examples)
```python
from medical_config import get_global_config
config = get_global_config()
```
Never show `from medical_config import config` (the direct singleton import) as the primary usage pattern — always show `get_global_config()`.

### Correct Threshold Values
**Source:** `src/medical_config.py` lines 35-51
**Apply to:** `README.md` (config reference), `IMPLEMENTATION_SUMMARY.md` (threshold table)
| Parameter | Correct Value | Stale Value in Old Docs |
|-----------|--------------|------------------------|
| CONFIDENCE_HIGH | 0.30 | 0.28 |
| CONFIDENCE_MEDIUM | 0.22 | 0.25 |
| HIGH_RISK_LOW_CONF_RATIO | 0.50 | (correct in CLAUDE.md) |
| TOP_K_FACTS | 5 | (correct) |

### Developer/Contributor Tone
**Source:** `CONTEXT.md` D-03 and specifics section
**Apply to:** All written files
- Third-person or imperative style only
- No "I created", "I noticed", "For my dissertation project", "This makes it easy for me"
- Lead with what the system does and how to use it, not why it was built

---

## No Analog Found

No files are without analogs — all content sources exist in the codebase. The key source files are:

| Target File Section | Source |
|---------------------|--------|
| All phase commands | `CLAUDE.md` Workflow section |
| Architecture overview | `CLAUDE.md` Architecture section + `ARCHITECTURE.md` |
| Config API (accessor methods, class name, thresholds) | `src/medical_config.py` |
| Component descriptions | `ARCHITECTURE.md` Core Abstractions section |
| Setup/install steps | `SETUP_GUIDE.md` (absorb then delete) |
| Known limitations to NOT repeat | `CONCERNS.md` — especially "IMPLEMENTATION_SUMMARY.md Documents Non-Existent API Surface" |

---

## Critical Accuracy Flags for Executor

These specific errors in current docs MUST NOT appear in any rewritten file:

1. **Class name:** Use `ConfigurationSettings`, not `MedicalVerificationConfig`
2. **Threshold values:** Use 0.30 / 0.22, not 0.28 / 0.25
3. **Preset classmethods:** `.production()`, `.development()`, `.testing()` do not exist — remove entirely
4. **`config_environment` param:** `MedicalVerifier.__init__()` has no such param — remove entirely
5. **`get_global_config(custom_config_path=...)`:** Function takes no arguments — remove entirely
6. **Phase count:** 6 phases, not 7. "Phase 7: Responsible AI Layer" is integrated into Phase 4
7. **Phase 6 script (old):** `evaluation_pipeline.py` / `evaluation_report_generator.py` do not exist; Phase 6 is `report_generator.py`
8. **Command format:** `python src/` only — no conda prefix
9. **`switch_to_testing_environment()`, `use_development_config()`, `verify_configuration_consistency()`:** Do not exist
10. **Validation claimed but absent (old docs):** `__post_init__` validation IS now implemented (Phase 2 added it); document it as real

---

## Metadata

**Analog search scope:** `D:\Report_verifier\` root docs, `src/`, `.planning/codebase/`, `.planning/phases/`
**Files scanned:** 9 (CLAUDE.md, workflow.txt, IMPLEMENTATION_SUMMARY.md, CONFIG_INTEGRATION_GUIDE.md, SETUP_GUIDE.md, src/medical_config.py, .planning/codebase/ARCHITECTURE.md, .planning/codebase/CONCERNS.md, .planning/ROADMAP.md)
**Pattern extraction date:** 2026-05-03
