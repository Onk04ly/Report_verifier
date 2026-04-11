# Architecture Research

## Suggested Component Boundaries

- KB Build Layer: PubMed acquisition + preprocessing + embedding generation
- Runtime Retrieval Layer: KB loading + FAISS index lifecycle
- Verification Layer: claim extraction + confidence + risk assessment + safety layer
- Reporting Layer: export and report rendering
- Quality Layer: tests, validation checks, and config governance

## Data Flow

1. Offline KB build creates CSV + embeddings.
2. Runtime verifier loads KB artifacts and retrieval index.
3. Claims are extracted and matched to evidence.
4. Risk/safety logic classifies outputs and flags review requirements.
5. Results are exported for report generation and analysis notebooks.

## Build Order

1. Contract/config alignment across existing modules
2. Safety logic hardening and input guards
3. Regression test suite for critical logic
4. Operational hardening (metadata + FAISS persistence)
5. Documentation alignment and workflow polish

---
*Generated: 2026-04-11*

