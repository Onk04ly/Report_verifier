# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Medical AI Hallucination Detection and Verification System — a dissertation research project. It analyzes medical texts to extract claims, verify them against a PubMed-sourced knowledge base, detect implausibilities/hallucinations, and produce risk-assessed reports.

## Environment Setup

```bash
pip install -r requirements.txt

# Required scispaCy model (not in requirements.txt):
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.6.2/en_core_sci_scibert-0.6.2.tar.gz

# NER and embedding models download automatically from HuggingFace on first run:
#   OpenMed/OpenMed-NER-PharmaDetect-SuperClinical-434M  (NER)
#   neuml/pubmedbert-base-embeddings                      (claim + KB embeddings)
```

## Workflow (6 Phases)

Run phases in order; each phase's outputs feed the next:

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

See `workflow.txt` for the complete phase guide.

## Architecture

### Data Pipeline

```
PubMed API
  → pubmed_fetcher.py          (rate-limited fetching, 500+ articles)
  → medical_preprocessor.py   (abbreviation expansion, entity extraction, SciBERT embeddings, quality grading)
  → claim_extractor_fixed.py  (FAISS index over KB embeddings, PubMedBERT claim embeddings, similarity scoring)
  → medical_verifier.py       (4-layer risk assessment + Responsible AI layer)
  → report_generator.py       (HTML/PDF output)
```

### Core Components

**`src/claim_extractor_fixed.py` — ClaimExtractor**
- Splits text into sentences via `en_core_sci_scibert` (scispaCy v0.6.2), identifies medical claims using regex + biomedical NER (`OpenMed/OpenMed-NER-PharmaDetect-SuperClinical-434M`)
- Embeds claims with `neuml/pubmedbert-base-embeddings`, searches against preprocessed KB via FAISS
- Confidence score = weighted blend of (avg similarity, max similarity, evidence quality, preprocessing quality)
- Detects negation/uncertainty patterns to adjust scores

**`src/medical_verifier.py` — MedicalVerifier**
- Orchestrates the pipeline; calls ClaimExtractor then applies 4-layer risk assessment:
  - Layer 1: Medical plausibility (physiological impossibilities, safety risks, evidence contradictions, logical consistency)
  - Layer 2: Content severity (critical/high-severity issue patterns)
  - Layer 3: Implausibility concerns
  - Layer 4: Confidence-based patterns (ratios of low-confidence claims)
- Applies Responsible AI safeguards: generates CRITICAL/HIGH/MEDIUM/CLINICAL safety warnings, detects dangerous terminology, flags for expert review

**`src/medical_config.py` — ConfigurationSettings (dataclass)**
- Single source of truth for all thresholds; import via `get_global_config()`
- Key methods: `get_confidence_thresholds()`, `get_safety_config()`, `get_risk_thresholds()`, `get_evidence_weights()`, `get_extraction_params()`, `get_disease_config()`, `get_outlier_params()`, `get_grade_weights()`
- No preset environments — edit field defaults directly to tune

**`src/medical_preprocessor.py`** — preprocessing for the knowledge base (not for input documents at runtime)

**`src/pubmed_fetcher.py`** — PubMed API client; set `NCBI_API_KEY` env var for 10 req/s instead of 3 req/s

### Key Data Files

| File | Purpose |
|------|---------|
| `data/expanded_knowledge_base_preprocessed.csv` | Primary KB used at runtime |
| `data/kb_embeddings_preprocessed.npy` | Pre-computed SciBERT embeddings; regenerating is slow |
| `outputs/medical_verification.json` | Structured verification results |

### Configuration

All threshold tuning happens in `src/medical_config.py`. Critical defaults:
- `HIGH_CONFIDENCE_THRESHOLD = 0.30`, `MEDIUM_CONFIDENCE_THRESHOLD = 0.22`
- `HIGH_RISK_LOW_CONF_RATIO = 0.50`
- `top_k_facts = 5`, `min_sentence_length = 8`

Do not hardcode thresholds in individual modules — always read from config.

## Knowledge Graph (RAG)

A graphify knowledge graph of this codebase lives in `graphify-out/`:

| File | Use |
|------|-----|
| `graphify-out/graph.json` | Full graph — 253 nodes, 353 edges, 13 communities |
| `graphify-out/GRAPH_REPORT.md` | God nodes, surprising connections, community map |
| `graphify-out/graph.html` | Interactive visualization (open in browser) |

**Before answering questions about codebase structure, architecture, or where something is defined — query the graph first:**

```bash
# BFS traversal — broad context around a concept
/graphify query "<question>"

# Trace a specific dependency path between two nodes
/graphify path "SourceNode" "TargetNode"

# Full explanation of a single node and all its connections
/graphify explain "NodeName"
```

Key god nodes (highest connectivity): `ClaimExtractor` (43 edges), `MedicalVerifier` (23), `MedicalPreprocessor` (21), `ConfigurationSettings` (11).

Run `/graphify --update` after adding or modifying files to keep the graph current.
