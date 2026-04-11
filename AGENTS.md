<!-- GSD:project-start source:PROJECT.md -->
## Project

**Medical AI Hallucination Detection and Verification System**

This is a brownfield research prototype that verifies medical claims from clinical text against a PubMed-derived knowledge base. It extracts claims, retrieves supporting evidence, scores confidence, and produces risk + safety outputs for clinician review. The primary users are dissertation stakeholders and technical evaluators focused on medical AI safety behavior.

**Core Value:** Potentially unsafe or implausible medical claims are identified reliably enough to trigger explicit expert-review decisions before trust is placed in generated medical text.

### Constraints

- **Domain Safety**: Medical outputs must always be framed as assistive and non-diagnostic — required for research ethics and safe usage.
- **Brownfield Compatibility**: New work must preserve current pipeline outputs and file formats unless migrations are explicitly defined.
- **Reproducibility**: Thresholds, scoring behavior, and KB artifact lineage must remain auditable for dissertation review.
- **Resource Profile**: Local CPU-first execution should remain viable; avoid requiring new heavy infrastructure for v1 improvements.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.8+ — all source code, scripts, and notebooks
## Runtime
- CPython 3.8+ (CPU-only configuration; GPU optional but not required)
- pip
- Lockfile: `requirements.txt` present (pinned with `>=` minimum versions, not exact pins)
## Frameworks
- `transformers>=4.20.0` — loads and runs Hugging Face models (Bio_ClinicalBERT, SciBERT)
- `sentence-transformers>=2.2.0` — sentence-level embedding utilities (imported alongside transformers)
- `torch>=1.12.0` — deep learning backend for all transformer inference (CPU build specified)
- `spacy>=3.4.0` — sentence splitting, linguistic pipeline
- `scispacy>=0.5.0` — scientific/medical spaCy extension (required to install biomedical NER models)
- `faiss-cpu>=1.7.0` — FAISS flat index for approximate nearest-neighbor search over KB embeddings; used in `src/claim_extractor_fixed.py` (`ClaimExtractor._init_retriever`)
- `scikit-learn>=1.1.0` — `cosine_similarity`, `TfidfVectorizer` (TF-IDF fallback in `MedicalPreprocessor`)
- `numpy>=1.21.0` — array math, memory-mapped `.npy` embedding loading
- `pandas>=1.5.0` — CSV I/O throughout; DataFrames are the primary in-memory table format
- `scipy>=1.9.0` — scientific computing utilities
- `matplotlib>=3.6.0` — static plots
- `seaborn>=0.11.0` — statistical visualization
- `plotly>=5.10.0` — interactive dashboard charts (used in Jupyter notebooks)
- `MedicalReportGenerator` (`src/report_generator.py`) — self-contained HTML report builder; no external PDF library detected (pure Python string templating, HTML output only)
- `jupyter>=1.0.0` + `notebook>=6.4.0` + `ipython>=8.5.0`
- Interactive analysis: `medical_verification_dashboard.ipynb`, `medical_verification_dashboard_1.ipynb`
- `requests>=2.28.0` — sole HTTP client; used exclusively in `src/pubmed_fetcher.py` for NCBI E-utilities calls
## ML Models
| Model | HuggingFace ID | Used By | Purpose |
|-------|---------------|---------|---------|
| Bio_ClinicalBERT | `emilyalsentzer/Bio_ClinicalBERT` | `ClaimExtractor` (`claim_extractor_fixed.py`) | Embed input claims at query time |
| SciBERT | `allenai/scibert_scivocab_uncased` | `MedicalPreprocessor` (`medical_preprocessor.py`) | Embed KB articles during preprocessing (offline) |
| BioClinicalBERT | `emilyalsentzer/Bio_ClinicalBERT` | `MedicalPreprocessor` | Secondary embedding method during preprocessing |
| en_ner_bc5cdr_md | spaCy model (scispacy v0.5.4) | `ClaimExtractor`, `MedicalPreprocessor` | Biomedical NER — chemicals and diseases (BC5CDR corpus) |
| en_core_sci_md | spaCy model (scispacy v0.5.4) | `ClaimExtractor` | Scientific sentence splitting (primary) |
| en_core_sci_sm | spaCy model (scispacy v0.5.4) | `ClaimExtractor` | Scientific sentence splitting (fallback) |
## Key Dependencies
- `faiss-cpu` — FAISS index is the entire retrieval mechanism; no fallback for runtime inference
- `transformers` + `torch` — Bio_ClinicalBERT claim embedding; fallback is `None` (basic tokenization only, severely degraded)
- `spacy` + `en_ner_bc5cdr_md` — raises `RuntimeError` if missing; hard dependency in `ClaimExtractor.__init__`
- `en_core_sci_md` or `en_core_sci_sm` — raises `RuntimeError` if neither is present
- `scikit-learn` — TF-IDF fallback in `MedicalPreprocessor` when transformers unavailable
- `pandas` — CSV data loading everywhere; practically required
## Configuration
- No `.env` file detected; API key for NCBI is currently hardcoded in `src/pubmed_fetcher.py` `main()` — should be moved to env var `NCBI_API_KEY`
- All model thresholds and algorithm parameters in `src/medical_config.py` via `ConfigurationSettings` dataclass
- Access via `get_global_config()`, `get_confidence_thresholds()`, `get_safety_config()`, `get_risk_thresholds()`, `get_evidence_weights()`, `get_extraction_params()`
- No build system (no `setup.py`, `pyproject.toml`, `Makefile`)
- Run phases directly: `python src/<module>.py`
## Platform Requirements
- Python 3.8+
- Minimum 8 GB RAM; 16 GB recommended
- Internet access for initial Hugging Face model downloads and PubMed API calls
- CPU-only PyTorch (GPU optional)
- No deployment infrastructure defined; dissertation research project, runs locally
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Snake_case for all Python modules: `claim_extractor_fixed.py`, `medical_verifier.py`, `medical_preprocessor.py`
- Suffix `_fixed` used to denote a revised version of a prior module (see `claim_extractor_fixed.py` — original is absent but name implies iteration)
- Utility/entry-point scripts are verb-noun: `pubmed_fetcher.py`, `report_generator.py`
- Config module is a noun: `medical_config.py`
- PascalCase throughout: `ClaimExtractor`, `MedicalVerifier`, `MedicalPreprocessor`, `MedicalReportGenerator`, `ExpandedPubMedFetcher`, `ConfigurationSettings`
- Class names are descriptive nouns or agent-nouns (Fetcher, Verifier, Extractor, Generator, Preprocessor)
- Snake_case: `verify_single_summary()`, `extract_claims_from_summary()`, `calculate_confidence_score()`
- Private methods prefixed with `_`: `_init_retriever()`, `_assess_overall_risk()`, `_apply_responsible_ai_layer()`, `_detect_medical_implausibility()`
- Internal sub-checks further suffixed with domain + `_optimized`: `_check_biological_impossibilities_optimized()`, `_check_evidence_based_violations_optimized()`
- Snake_case: `claim_lower`, `supporting_facts`, `low_conf_ratio`, `embeddings_cache_path`
- Config constants are SCREAMING_SNAKE_CASE on the dataclass: `CONFIDENCE_HIGH`, `HIGH_RISK_THRESHOLD`, `TOP_K_FACTS`
- Ratio variables follow `{domain}_ratio` pattern: `low_conf_ratio`, `negation_ratio`, `uncertainty_ratio`
- Snake_case strings throughout: `'verification_confidence'`, `'claim_text'`, `'safety_warnings'`, `'requires_expert_review'`
- Risk level values use SCREAMING_SNAKE_CASE strings: `'CRITICAL_RISK'`, `'HIGH_RISK'`, `'MEDIUM_RISK'`, `'LOW_RISK'`
- Confidence level values also use caps: `'HIGH'`, `'MEDIUM'`, `'LOW'`
## Module Structure Pattern
## Configuration Access Pattern
- `get_global_config().get_confidence_thresholds()`
- `get_global_config().get_safety_config()`
- `get_global_config().get_risk_thresholds()`
- `get_global_config().get_evidence_weights()`
- `get_global_config().get_extraction_params()`
## Docstring Style
## Type Annotations
## Error Handling Patterns
## Logging / Print Patterns
- No emoji (plain text) for informational messages in `ClaimExtractor`
- ` ` / ` ` prefix for success/warning in `MedicalVerifier.__init__`
- ` SAFETY ALERT:` prefix for safety events
- ` ` prefix for safety/compliance messages in export methods
## Class Design Patterns
## Notable Anti-Patterns / Deviations
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Offline knowledge base construction (Phase 1–2) is separate from runtime inference (Phase 3–4)
- Each phase writes file artifacts consumed by the next phase; components do not call each other at runtime except through `MedicalVerifier` → `ClaimExtractor`
- All configurable thresholds are centralised in a single dataclass singleton (`src/medical_config.py`); no module hardcodes threshold values
- Responsible AI safeguards are integrated directly into the main verification pipeline, not as a post-processing step
## Layers
- Purpose: Build and embed the PubMed evidence corpus
- Scripts: `src/pubmed_fetcher.py`, `src/medical_preprocessor.py`
- Outputs: `data/expanded_knowledge_base_preprocessed.csv`, `data/kb_embeddings_preprocessed.npy`
- Depends on: PubMed E-utilities API (NCBI), `allenai/scibert_scivocab_uncased`, `emilyalsentzer/Bio_ClinicalBERT`
- Used by: `src/claim_extractor_fixed.py` at initialisation time
- Purpose: Approximate nearest-neighbour search over KB embeddings
- Location: Constructed in `ClaimExtractor._init_retriever()` / `_create_optimized_faiss_index()`
- In-memory FAISS `IndexFlatL2` built from `data/kb_embeddings_preprocessed.npy`
- Used by: `ClaimExtractor.retrieve_supporting_facts()`
- Purpose: Sentence splitting, medical entity recognition, claim classification, embedding, and retrieval
- Location: `src/claim_extractor_fixed.py` — class `ClaimExtractor`
- Depends on: SpaCy models (`en_ner_bc5cdr_md`, `en_core_sci_md`/`en_core_sci_sm`), `Bio_ClinicalBERT`, FAISS index
- Used by: `MedicalVerifier.verify_single_summary()`
- Purpose: Multi-layer clinical risk scoring and safety warning generation
- Location: `src/medical_verifier.py` — class `MedicalVerifier`
- Depends on: `ClaimExtractor`, `src/medical_config.py`
- Outputs: structured result dicts written to `outputs/medical_verification.json` and `outputs/medical_verification.csv`
- Purpose: Render HTML/PDF reports from verification result JSON
- Location: `src/report_generator.py` — class `MedicalReportGenerator`
- Depends on: `outputs/medical_verification.json`
## Data Flow
- No shared in-memory state between pipeline runs; all state passes through file artifacts or function return values
- `config` singleton in `src/medical_config.py` is module-level and shared across all importers in the same process
## 4-Layer Risk Assessment (`MedicalVerifier._assess_overall_risk()`)
- `_detect_medical_implausibility()` dispatches to four sub-analyses:
- `_check_evidence_based_validity()` matches claim text against 13 established-fact patterns via compiled regex (insulin_dependency, cardiac_emergency, cancer_treatment_evidence, anaphylaxis_treatment, stroke_emergency, meningitis_severity, sepsis_treatment, vaccine_safety, high_risk_pregnancy, autoimmune_management, genetic_disorders, severe_mental_illness, drug_interactions)
- Result: CRITICAL_RISK if any CRITICAL severity issue found; HIGH_RISK if ≥2 high-severity issues or ≥2 very-low-confidence claims
- Aggregates HIGH-severity issues and violations; triggers HIGH_RISK if combined count ≥ 2
- Any remaining implausibility issues → HIGH_RISK regardless of count
- `low_conf_ratio >= HIGH_RISK_LOW_CONF_RATIO (0.50)` → HIGH_RISK
- `low_conf_ratio >= MEDIUM_RISK_LOW_CONF_RATIO (0.30)` or mixed medium pattern → MEDIUM_RISK
- `high_conf_ratio >= LOW_RISK_HIGH_CONF_RATIO (0.40)` → LOW_RISK
- Otherwise → MEDIUM_RISK
- Augmented by negation ratio (`> 0.30`) and uncertainty ratio (`> 0.50`) as additional risk factors
## Responsible AI Layer (`MedicalVerifier._apply_responsible_ai_layer()`)
- **Safety warnings** at four levels: CRITICAL, HIGH, MEDIUM, CLINICAL
- **`requires_expert_review`** flag (bool): set when any warning reaches HIGH or CRITICAL
- **`auto_flagged`** flag (bool): set when `low_conf_ratio >= 0.40` or CRITICAL warning present
- **`responsible_ai_disclaimer`**: structured disclaimer with `notice`, `limitations`, and `proper_use` lists
- **`safety_assessment`**: numeric summary including `dangerous_terms_detected` list
## Core Abstractions
- `@dataclass` with all numeric thresholds as typed fields
- Module-level singleton: `config = ConfigurationSettings()`
- Accessor functions: `get_global_config()`, `get_confidence_thresholds()`, `get_safety_config()`, `get_risk_thresholds()`
- Key thresholds: `CONFIDENCE_HIGH=0.30`, `CONFIDENCE_MEDIUM=0.22`, `HIGH_RISK_LOW_CONF_RATIO=0.50`, `CRITICAL_THRESHOLD=0.50`, `TOP_K_FACTS=5`, `MIN_SENTENCE_LENGTH=8`
- Import pattern used by all other modules: `from medical_config import get_global_config`
- Wraps NCBI E-utilities (`esearch.fcgi`, `efetch.fcgi`) with adaptive rate limiting (0.05s with API key, 0.35s without)
- `search_pubmed_segmented()` — year-by-year + journal-filter segmentation to surpass NCBI's 10 000 result cap
- `fetch_abstracts()` — batch XML parsing, extracts PMID, title, abstract, year
- `create_expanded_medical_knowledge_base()` — orchestrates 130+ queries, deduplicates, saves CSV + summary CSV
- Offline preprocessing only; not called at runtime by the verifier
- Methods: `normalize_text()` (abbreviation expansion via 40-entry dict), `extract_medical_entities()` (SpaCy `en_ner_bc5cdr_md`, labels DISEASE/CHEMICAL/DRUG), `calculate_quality_score()`, `detect_negation_uncertainty()`, `grade_evidence_quality()` (A/B/C/D based on title/source regex), `categorize_by_specialty()` (10 medical specialties)
- Embedding hierarchy: SciBERT (primary) → BioClinicalBERT (secondary) → TF-IDF (fallback), all using CLS-token pooling at 512-token max length
- Loaded once per process; initialisation is the most expensive step (~seconds to load BERT + build FAISS index)
- `_init_retriever()` — prefers `data/expanded_knowledge_base_preprocessed.csv` with selective column loading; falls back to raw CSV; loads or generates `.npy` embeddings
- `identify_medical_claims()` — 25+ compiled regex patterns; 10 claim types: diagnosis, medication, symptom, medical_history, procedure, vital_signs, outcome, clinical_assessment, temporal, test_result, entity_based
- `calculate_confidence_score()` — weighted blend + five ensemble penalties: `_check_biological_impossibilities_optimized`, `_check_evidence_based_violations_optimized`, `_check_treatment_efficacy_optimized`, `_check_timeline_plausibility_optimized`, `_check_contraindications_optimized`; final penalty = max of the five; `composite_score - total_penalty`
- `get_sentence_embedding()` — `Bio_ClinicalBERT` mean-pooled last hidden state; fallback to word-count features
- Instantiates `ClaimExtractor` in `__init__`; loads safety config from `get_global_config()`
- Public API: `verify_single_summary(text, id)`, `verify_multiple_summaries(list)`, `verify_from_csv(path)`, `verify_from_claim_extractor_json(path)`
- `export_results(results, path, format)` — supports `json` and `csv`; always writes accompanying `_safety_log.json`
- Reads from `outputs/medical_verification.json`
- `generate_html_report()` — produces self-contained HTML with inline CSS; risk-level colour coding (green/amber/red); per-claim confidence colour coding; negation/uncertainty metrics grid
- No external template engine; HTML is constructed as f-strings
## Component Communication
| From | To | Mechanism |
|------|-----|-----------|
| `pubmed_fetcher.py` | `medical_preprocessor.py` | File: `data/expanded_knowledge_base.csv` |
| `medical_preprocessor.py` | `claim_extractor_fixed.py` | Files: `data/expanded_knowledge_base_preprocessed.csv`, `data/kb_embeddings_preprocessed.npy` |
| `claim_extractor_fixed.py` | `medical_verifier.py` | Direct instantiation; `ClaimExtractor.extract_claims_from_summary()` called inside `MedicalVerifier.verify_single_summary()` |
| `medical_verifier.py` | `report_generator.py` | File: `outputs/medical_verification.json` |
| `medical_config.py` | all other modules | Module-level singleton; imported with `from medical_config import get_global_config` |
## Key Data Structures
```python
```
```python
```
```python
```
## Error Handling
- SpaCy model loading: `try/except OSError` with fallback model; raises `RuntimeError` only if no model is available at all
- BERT model loading: `try/except Exception`; sets `self.tokenizer = None`; `get_sentence_embedding()` falls back to word-count features
- FAISS index loading: catches `Exception`, re-generates embeddings from scratch
- PubMed API calls: `try/except Exception` per batch; failed batches are skipped with a longer sleep
- All `export_results()` calls validate safety before writing
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
