# Medical AI Hallucination Detection and Verification System

A dissertation research project that analyzes medical texts to extract claims, verify them against a PubMed-sourced knowledge base, detect implausibilities and hallucinations, and produce risk-assessed reports.

---

## Table of Contents

1. [Project Overview and Architecture](#project-overview-and-architecture)
2. [Setup and Installation](#setup-and-installation)
3. [Usage / Phase Commands](#usage--phase-commands)
4. [Configuration Reference](#configuration-reference)

---

## Project Overview and Architecture

### Data Pipeline

```
PubMed API
  → pubmed_fetcher.py          (rate-limited fetching, 500+ articles)
  → medical_preprocessor.py   (abbreviation expansion, entity extraction, SciBERT embeddings, quality grading)
  → claim_extractor_fixed.py  (FAISS index over KB embeddings, Bio_ClinicalBERT claim embeddings, similarity scoring)
  → medical_verifier.py       (4-layer risk assessment + Responsible AI layer)
  → report_generator.py       (HTML/PDF output)
```

### Key Components

| Component | File | Role |
|-----------|------|------|
| ClaimExtractor | src/claim_extractor_fixed.py | Sentence splitting, NER, claim classification, FAISS retrieval, confidence scoring |
| MedicalVerifier | src/medical_verifier.py | Orchestrates pipeline; 4-layer risk assessment; Responsible AI layer |
| ConfigurationSettings | src/medical_config.py | Centralized config singleton; all thresholds loaded via `get_global_config()` |
| MedicalPreprocessor | src/medical_preprocessor.py | Offline KB preprocessing only; not called at runtime |
| MedicalReportGenerator | src/report_generator.py | Reads `outputs/medical_verification.json`; produces self-contained HTML |

### Key Data Files

| File | Purpose |
|------|---------|
| `data/expanded_knowledge_base_preprocessed.csv` | Primary KB used at runtime |
| `data/kb_embeddings_preprocessed.npy` | Pre-computed SciBERT embeddings; regenerating is slow |
| `outputs/medical_verification.json` | Structured verification results |

### Risk Assessment Layers

`MedicalVerifier` applies a 4-layer risk assessment to each document:

- **Layer 1 — Medical plausibility:** Detects physiological impossibilities, safety risks, evidence contradictions, and logical consistency violations.
- **Layer 2 — Content severity:** Matches critical and high-severity issue patterns.
- **Layer 3 — Implausibility concerns:** Flags implausible medical claims.
- **Layer 4 — Confidence-based patterns:** Triggers when the ratio of low-confidence claims exceeds `HIGH_RISK_LOW_CONF_RATIO` (default: 0.50).

The Responsible AI layer generates CRITICAL/HIGH/MEDIUM/CLINICAL safety warnings, detects dangerous terminology, and flags documents for expert review.

---

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- At least 8GB RAM (16GB recommended)
- Internet connection for model downloads

### Install Core Dependencies

```bash
pip install -r requirements.txt
```

### Install SpaCy Medical Models

These models are required but are not included in `requirements.txt`:

```bash
# Install medical entity recognition model
python -m spacy download en_ner_bc5cdr_md

# Alternative if the above command fails:
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz

# Scientific text processing models:
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `NCBI_API_KEY` | Optional | Increases PubMed rate limit from 3 req/s to 10 req/s (Phase 1 only) |

### Troubleshooting

1. **SpaCy model download fails** — Use the direct URL pip install form shown above. Check internet connectivity and available disk space.
2. **Memory issues** — 16GB RAM recommended. Close other applications before running Phases 3–4.
3. **FAISS installation issues** — Use `faiss-cpu` for CPU-only systems: `pip install faiss-cpu`.
4. **Transformers model loading slow** — Models download on first use; subsequent loads use the local cache. Setting `TRANSFORMERS_CACHE` to a fast local path speeds up reruns.

---

## Usage / Phase Commands

Run phases in order — each phase's outputs feed the next.

```bash
# Phase 1 — Fetch PubMed data → data/expanded_knowledge_base.csv
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

**Note:** Phases 1 and 2 are run once to build the knowledge base. Phases 3–6 are the runtime workflow applied to each new input document.

See `workflow.txt` for the complete phase guide.

---

## Configuration Reference

All threshold tuning happens in `src/medical_config.py`. The class `ConfigurationSettings` is the single source of truth — no module hardcodes threshold values inline.

### Import Pattern

```python
from medical_config import get_global_config

config = get_global_config()
thresholds = config.get_confidence_thresholds()   # → {'high': 0.30, 'medium': 0.22}
params = config.get_extraction_params()           # → {'top_k_facts': 5, ...}
```

### Key Threshold Values

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `CONFIDENCE_HIGH` | 0.30 | Claims above this = HIGH confidence |
| `CONFIDENCE_MEDIUM` | 0.22 | Claims above this = MEDIUM confidence |
| `HIGH_RISK_LOW_CONF_RATIO` | 0.50 | 50%+ low-confidence claims triggers HIGH RISK (Layer 4) |
| `TOP_K_FACTS` | 5 | KB facts retrieved per claim |
| `MIN_SENTENCE_LENGTH` | 8 | Minimum words to process a sentence |

### Accessor Methods

| Method | Returns |
|--------|---------|
| `config.get_confidence_thresholds()` | Confidence band thresholds (`high`, `medium`) |
| `config.get_safety_config()` | Risk flagging thresholds (high-risk, critical, expert-review, auto-flag) |
| `config.get_risk_thresholds()` | Layer 4 confidence-ratio thresholds |
| `config.get_evidence_weights()` | Confidence score component weights (must sum to 1.0) |
| `config.get_extraction_params()` | Retrieval and claim extraction parameters |
| `config.get_disease_config()` | Phase 5 disease specialization settings |
| `config.get_outlier_params()` | Distance normalization and outlier penalty constants |
| `config.get_grade_weights()` | Evidence grade letter-to-numeric weight mapping |

### Configuration Validation

`ConfigurationSettings.__post_init__()` validates every field at construction time. If any invariant is violated (e.g., `CONFIDENCE_MEDIUM >= CONFIDENCE_HIGH`, weights not summing to 1.0), construction raises `ValueError` with a complete diagnostic listing all invalid fields. Invalid configuration cannot propagate into extraction or scoring logic.

---

For a developer deep-dive into module internals, NER patterns, FAISS index construction, and the Responsible AI layer, see `CLAUDE.md`.
