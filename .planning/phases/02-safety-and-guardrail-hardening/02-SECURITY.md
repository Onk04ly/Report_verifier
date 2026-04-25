---
phase: "02"
slug: safety-and-guardrail-hardening
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-25
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User input → MedicalVerifier | `verify_single_summary(medical_summary, summary_id)` — arbitrary string from caller | Unvalidated text; may be oversized, non-string, or adversarially crafted |
| Filesystem → ClaimExtractor | `data/dangerous_guidance_seeds.json` loaded at init | Seed phrase list; integrity = repo integrity |
| MedicalVerifier → Filesystem | `export_results()` writes main JSON + per-result sidecar files | Structured JSON; sidecar path derived from `summary_id` |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Tampering | data/dangerous_guidance_seeds.json | accept | File checked into git; structural assertions in conftest + test_sidecar_seeds_file_status | closed |
| T-02-02 | DoS | Wave-0 stubs permanently red | mitigate | All 14 test stubs are now concrete assertions (no skip/xfail/pass stubs remain in test_safety_guards.py) | closed |
| T-02-03 | Tampering | ConfigurationSettings | mitigate | `__post_init__` calls `_check_probability` on DANGEROUS_SEMANTIC_THRESHOLD and DUPLICATE_SENTENCE_RATIO, `_check_positive_int` on MAX_SUMMARY_CHARS; ValueError raised on violation | closed |
| T-02-04 | DoS | MAX_SUMMARY_CHARS misconfig (too high) | accept | No upper bound enforced — solo operator, user-foot-gun not adversarial; see Accepted Risks | closed |
| T-02-05 | Tampering (path traversal) | seeds_path construction | mitigate | Path hard-coded via `os.path.join(os.path.dirname(__file__), '..', 'data', 'dangerous_guidance_seeds.json')` — no user input enters path | closed |
| T-02-06 | DoS (malformed JSON) | json.load on seeds | mitigate | Wrapped in try/except; sets `_seeds_file_status='error'`, `danger_centroid=None`; pipeline continues in degraded mode | closed |
| T-02-07 | EoP (false safety — zero centroid) | Empty phrases list | mitigate | `if not all_phrases:` guard sets `_seeds_file_status='error'`, bypasses centroid computation; `danger_centroid` stays None | closed |
| T-02-08 | DoS (oversized claim count) | identify_medical_claims | mitigate | `claims[:max_claims]` hard slice at MAX_CLAIMS_PER_SUMMARY=50 in `extract_claims_from_summary` | closed |
| T-02-09 | Tampering (shape mismatch crash) | cosine similarity | mitigate | `np.asarray(..., dtype=np.float32)` on both vectors in `is_semantically_dangerous`; `reshape(1,-1)` on both sides in `calculate_confidence_score` | closed |
| T-02-10 | DoS (memory exhaustion) | Oversized summary string | mitigate | `medical_summary[:max_chars]` truncation in `verify_single_summary` before extractor; `original_char_count` preserved | closed |
| T-02-11 | DoS (unhandled exception) | Non-string / empty input | mitigate | `isinstance(..., str)` and `.strip()` checks return `_make_unknown_result(...)` early with `input_validation.error` set | closed |
| T-02-12 | Tampering (inflated claim counts via duplication) | Repeated-content input | mitigate | `_sentence_duplication_ratio()` sets `input_validation['warning']='repeated_content'` when above DUPLICATE_SENTENCE_RATIO | closed |
| T-02-13 | EoP (false safety under degraded model) | sentence_model None | mitigate | `risk_assessment['degraded_mode'] = True` set in `verify_single_summary` when `self.extractor.sentence_model is None` | closed |
| T-02-14 | Injection (input_validation field spoofing) | caller passing pre-populated result | accept | Solo local workflow — same caller and implementer; no multi-tenant input vector; see Accepted Risks | closed |
| T-02-15 | Tampering (path traversal via summary_id) | sidecar_path construction | mitigate | `summary_id = os.path.basename(str(raw_id))` strips path separators before sidecar filename is constructed | closed |
| T-02-16 | DoS (sidecar write fails, halts export) | json.dump in sidecar writer | mitigate | Per-result write wrapped in try/except; failing sidecar prints warning and does not abort export loop | closed |
| T-02-17 | Information disclosure | unavailable_models in sidecar | accept | Contains only public HuggingFace model IDs already present in source code; see Accepted Risks | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-04 | MAX_SUMMARY_CHARS has no upper bound. Only the pipeline operator (sole developer) can set this value; an excessively large value is a user foot-gun, not an adversarial input path. | Onk04ly | 2026-04-25 |
| AR-02-02 | T-02-14 | No multi-tenant trust boundary exists between caller and `verify_single_summary`. Solo local workflow — caller and implementer are the same person; field spoofing from an upstream caller is not a realistic threat. | Onk04ly | 2026-04-25 |
| AR-02-03 | T-02-17 | `unavailable_models` in sidecar JSON contains only `neuml/pubmedbert-base-embeddings` — a public HuggingFace model ID already present in source code. No private credentials or internal paths are exposed. | Onk04ly | 2026-04-25 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-25 | 17 | 17 | 0 | gsd-security-auditor (claude-sonnet-4-6) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter
