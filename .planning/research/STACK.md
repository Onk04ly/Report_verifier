# Stack Research

## Current Stack (Observed)

- Language/runtime: Python 3.8+
- NLP and ML: `transformers`, `torch`, `spacy`, `scispacy`, `sentence-transformers`
- Retrieval: `faiss-cpu`
- Data processing: `pandas`, `numpy`, `scikit-learn`
- Reporting/analysis: Jupyter notebooks, HTML report generator

## Recommended Direction

- Keep Python-centric architecture for continuity with existing assets.
- Preserve FAISS + embedding pipeline for current scale; focus on reproducibility and robustness before stack changes.
- Introduce standard `logging` and `pytest` as baseline engineering tools.

## Risks To Manage

- Model download/runtime dependency fragility (SpaCy medical models + HF model availability).
- Silent degraded mode if BERT loading fails.
- Threshold/config drift across modules.

---
*Generated: 2026-04-11*

