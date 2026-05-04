# Medical Verification System — Implementation Summary

## Overview

This document is the architecture and configuration reference for the Medical AI Hallucination Detection and Verification System. For setup and phase execution commands, see `README.md`. For developer deep-dives into module internals, see `CLAUDE.md`.

---

## Configuration (`src/medical_config.py`)

### Class: `ConfigurationSettings`

A `@dataclass` singleton that is the single source of truth for all runtime thresholds and parameters. No module may define its own inline threshold values.

Construction is validated immediately: `__post_init__()` checks every field and raises `ValueError` with a complete diagnostic listing all invalid fields if any invariant is violated. Invalid config cannot propagate into scoring or extraction logic.

### Import Pattern

```python
from medical_config import get_global_config

config = get_global_config()
thresholds = config.get_confidence_thresholds()
params = config.get_extraction_params()
```

The module exposes a validated singleton at import time (`config = ConfigurationSettings()`). `get_global_config()` returns this instance. The function takes no arguments.

### Accessor Methods

| Method | Returns | Example values |
|--------|---------|----------------|
| `get_confidence_thresholds()` | `Dict[str, float]` | `{'high': 0.30, 'medium': 0.22}` |
| `get_safety_config()` | `Dict[str, float]` | `{'high_risk_threshold': 0.30, 'critical_threshold': 0.50, 'require_expert_review_threshold': 0.20, 'auto_flag_threshold': 0.40}` |
| `get_risk_thresholds()` | `Dict[str, float]` | `{'high_risk_low_conf_ratio': 0.50, 'medium_risk_low_conf_ratio': 0.30, 'low_risk_high_conf_ratio': 0.40, 'high_negation_ratio': 0.30, 'high_uncertainty_ratio': 0.50}` |
| `get_evidence_weights()` | `Dict[str, float]` | `{'similarity_avg': 0.40, 'similarity_max': 0.20, 'distance': 0.20, 'evidence_quality': 0.20}` |
| `get_extraction_params()` | `Dict[str, int]` | `{'top_k_facts': 5, 'confidence_facts_count': 3, 'min_sentence_length': 8, 'max_claims_per_summary': 50}` |
| `get_disease_config()` | `Dict[str, Any]` | Disease specialization settings (Phase 5) |
| `get_outlier_params()` | `Dict[str, float]` | Distance normalization and outlier penalty constants |
| `get_grade_weights()` | `Dict[str, float]` | `{'A': 1.0, 'B': 0.8, 'C': 0.6, 'D': 0.4}` |

### Key Threshold Values

| Field | Default | Purpose |
|-------|---------|---------|
| `CONFIDENCE_HIGH` | 0.30 | Claims above this = HIGH confidence |
| `CONFIDENCE_MEDIUM` | 0.22 | Claims above this = MEDIUM confidence |
| `HIGH_RISK_LOW_CONF_RATIO` | 0.50 | 50%+ low-confidence claims → HIGH RISK (Layer 4) |
| `MEDIUM_RISK_LOW_CONF_RATIO` | 0.30 | 30%+ low-confidence claims → MEDIUM RISK (Layer 4) |
| `LOW_RISK_HIGH_CONF_RATIO` | 0.40 | 40%+ high-confidence claims → LOW RISK (Layer 4) |
| `TOP_K_FACTS` | 5 | KB facts retrieved per claim |
| `MIN_SENTENCE_LENGTH` | 8 | Minimum sentence length in words |
| `MAX_CLAIMS_PER_SUMMARY` | 50 | Hard cap on claims extracted per input |
| `DANGEROUS_SEMANTIC_THRESHOLD` | 0.75 | Cosine similarity cutoff for dangerous-guidance centroid match |
| `MAX_SUMMARY_CHARS` | 5000 | Input validation hard truncation limit |

### Configuration Validation

`ConfigurationSettings.__post_init__()` validates at construction time:
- All probability fields are in [0.0, 1.0]
- `CONFIDENCE_HIGH > CONFIDENCE_MEDIUM` ordering invariant
- Evidence weights sum to 1.0 (within 1e-6 tolerance)
- Dataset split fractions (holdout + tune + train) sum to 1.0
- All positive-integer fields are > 0

Validation raises `ValueError` listing every invalid field in a single pass. Run `python -c "from medical_config import get_global_config; get_global_config().print_config()"` to print current values to stdout.

### Modifying Configuration

Edit field values directly in `ConfigurationSettings` defaults or create a subclass. There are no preset environment classmethods — the `ConfigurationSettings` dataclass does not expose factory methods for named environments such as production, development, or testing. All tuning is done by editing the field defaults or assigning to the `config` singleton after import.

---

## Component Overview

### `ClaimExtractor` (`src/claim_extractor_fixed.py`)

Loads once per process; initialisation is the most expensive step (BERT model load + FAISS index build).

- Embeds claims using `Bio_ClinicalBERT` (mean-pooled last hidden state); falls back to word-count features if model is unavailable
- Builds a FAISS `IndexFlatL2` over `data/kb_embeddings_preprocessed.npy`
- Identifies medical claims via 25+ compiled regex patterns across 10 claim types (diagnosis, medication, symptom, medical_history, procedure, vital_signs, outcome, clinical_assessment, temporal, test_result, entity_based)
- `calculate_confidence_score()`: weighted blend (avg similarity 0.40, max similarity 0.20, distance 0.20, evidence quality 0.20) minus max of 5 ensemble plausibility penalties
- `retrieve_supporting_facts()`: accepts optional `disease_bucket_indices` parameter for disease-scoped retrieval (Phase 5)

### `MedicalVerifier` (`src/medical_verifier.py`)

Orchestrates the full pipeline.

- Instantiates `ClaimExtractor` in `__init__`; loads all thresholds via `get_global_config()`
- Public API: `verify_single_summary(text, id)`, `verify_multiple_summaries(list)`, `verify_from_csv(path)`, `verify_from_claim_extractor_json(path)`, `verify_for_disease(text, disease_slug)` (Phase 5)
- Applies 4-layer risk model (see below)
- Applies Responsible AI layer after risk assessment
- `export_results()` writes `outputs/medical_verification.json`, `outputs/medical_verification.csv`, and `outputs/medical_verification_safety_log.json`

### `ConfigurationSettings` (`src/medical_config.py`)

See Configuration section above.

### `MedicalPreprocessor` (`src/medical_preprocessor.py`)

Offline KB preprocessing only — not called at runtime. Generates SciBERT embeddings and quality grades for PubMed articles. Run once after Phase 1 (data collection).

### `MedicalReportGenerator` (`src/report_generator.py`)

Reads `outputs/medical_verification.json`; produces a self-contained HTML report with inline CSS and per-claim risk-level colour coding.

### Phase 5 Components (specialist scope)

- `src/disease_buckets.py` — `DiseaseKBBuckets`: centroid computation and KB article assignment via cosine similarity >= 0.60
- `src/disease_evaluator.py` — `DiseaseEvaluator`: tertile-stratified dataset splits (20/60/20); per-disease precision/accuracy report to `outputs/disease_eval_report.json`
- `src/expansion_gate.py` — `ExpansionGate`: persistent run counter; consecutive-pass streak; gates broad multi-disease expansion until specialist metrics pass target thresholds

---

## 4-Layer Risk Assessment

Layers are evaluated in priority order; a higher-priority match short-circuits lower layers.

| Layer | Trigger | Outcome |
|-------|---------|---------|
| 1 — Medical Plausibility | Physiological impossibilities, patient safety risks, evidence contradictions, logical inconsistency | CRITICAL_RISK on any CRITICAL issue; HIGH_RISK if >= 2 high-severity issues |
| 2 — Severity Count | Combined HIGH-severity issues + violations >= 2 | HIGH_RISK |
| 3 — Implausibility Presence | Any implausibility issue present | HIGH_RISK |
| 4 — Confidence Ratio (default) | low_conf_ratio >= 0.50 → HIGH; >= 0.30 → MEDIUM; high_conf_ratio >= 0.40 → LOW; otherwise MEDIUM | Level by ratio |

The Responsible AI layer runs after risk assessment and appends `results['responsible_ai']` with safety warnings (CRITICAL/HIGH/MEDIUM/CLINICAL), `requires_expert_review` flag, `auto_flagged` flag, and a structured disclaimer.

---

## Component Communication

| From | To | Mechanism |
|------|----|-----------|
| `pubmed_fetcher.py` | `medical_preprocessor.py` | File: `data/expanded_knowledge_base.csv` |
| `medical_preprocessor.py` | `claim_extractor_fixed.py` | Files: `data/expanded_knowledge_base_preprocessed.csv`, `data/kb_embeddings_preprocessed.npy` |
| `claim_extractor_fixed.py` | `medical_verifier.py` | Direct instantiation; `ClaimExtractor.extract_claims_from_summary()` called inside `MedicalVerifier.verify_single_summary()` |
| `medical_verifier.py` | `report_generator.py` | File: `outputs/medical_verification.json` |
| `medical_config.py` | all other modules | Module-level singleton; imported with `from medical_config import get_global_config` |

---

*Source of truth for all threshold values and API signatures: `src/medical_config.py`*
*Last updated: Phase 6 Documentation Alignment*
