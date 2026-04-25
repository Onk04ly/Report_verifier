# Phase 2: Safety and Guardrail Hardening - Research

**Researched:** 2026-04-15
**Domain:** Python input validation, semantic similarity (numpy/sklearn), JSON seeds file design, model degraded-mode signaling, pytest contract testing
**Confidence:** HIGH — all findings are verified directly from the codebase, requirements.txt, and existing test patterns

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SAFE-01: Semantic Danger Detection**
- Prototype similarity using `neuml/pubmedbert-base-embeddings` (already loaded as `self.sentence_model` in ClaimExtractor)
- Seeds live in `data/dangerous_guidance_seeds.json` — JSON with `{ "version": "1.0", "categories": { "<name>": ["phrase1", ...] } }`
- Required categories: `medication_discontinuation`, `treatment_avoidance`, `dangerous_alternatives`, `emergency_minimization`, `vaccine_misinformation`
- Runtime: flatten all phrases → encode all with pubmedbert → compute single global centroid vector
- Centroid cached as instance attribute on ClaimExtractor (recomputed once at init)
- Danger check: cosine similarity of claim embedding vs centroid > `DANGEROUS_SEMANTIC_THRESHOLD`
- Threshold stored as `DANGEROUS_SEMANTIC_THRESHOLD` in `MedicalVerificationConfig` (not hardcoded)
- Flag trigger: existing rule match OR semantic similarity above threshold (either = flag)
- Seeds loaded in `ClaimExtractor.__init__()` after embedding model loads; if missing → log warning, semantic check skipped (recorded in model_status sidecar)

**SAFE-02a: Input Validation**
- Soft-flag + truncate at `MedicalVerifier.verify_single_summary()` entry, before ClaimExtractor is called
- `MAX_SUMMARY_CHARS` in `MedicalVerificationConfig`; truncate + set `input_validation.truncated: true`
- Malformed checks in order: non-string → early return UNKNOWN; empty/whitespace → early return UNKNOWN; oversized → truncate + flag; high duplication ratio → flag (continue); no entities → flag post-NER inside extractor
- All signals in top-level `input_validation` dict on result

**SAFE-02b: Max-Claims Enforcement**
- `MAX_CLAIMS_PER_SUMMARY = 50` in `MedicalVerificationConfig` (field already exists — confirmed in code)
- Enforcement inside `ClaimExtractor.extract_claims_from_summary()` after identification, before embedding
- First-N by sentence order; add `claims_truncated: true` and `claims_truncated_count: N` to result dict

**SAFE-03: Degraded Mode Signaling**
- Critical model: `neuml/pubmedbert-base-embeddings` (`self.sentence_model`). If `None`: use word-count fallback
- Set `result['risk_assessment']['degraded_mode'] = True`
- Sidecar at `outputs/<summary_id>_model_status.json` — written alongside every export
- Sidecar structure: `{ summary_id, timestamp, degraded_mode, unavailable_models, fallbacks_used, seeds_file_status }`

### Claude's Discretion
None — all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)
None raised during discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAFE-01 | System detects unsafe medical guidance using hybrid rule + semantic checks, not exact keyword matching only | Semantic centroid approach using existing SentenceTransformer; cosine similarity via sklearn already imported in ClaimExtractor |
| SAFE-02 | System validates input size/shape and enforces claim extraction limits from configuration | verify_single_summary() is the single call-path entry; MAX_CLAIMS_PER_SUMMARY already exists in config; duplication check is stdlib-only |
| SAFE-03 | System marks or fails degraded mode when critical embedding models are unavailable | self.sentence_model is None is the existing fallback signal; sidecar pattern follows export_results() convention |
</phase_requirements>

---

## Summary

Phase 2 adds four independent capabilities to the existing pipeline: semantic danger detection, input validation, max-claims enforcement, and degraded-mode signaling. All four interact with code that is already read-clean after Phase 1 — config is centralized, claim schema is locked, and export paths are deterministic.

The most technically nuanced piece is SAFE-01: computing a centroid from seed embeddings and using cosine similarity against it. The pattern is already present in the codebase (`calculate_confidence_score` does exactly this with `cosine_similarity` from sklearn), so no new dependency is introduced. The centroid must be computed from float32 numpy arrays and stored as a class attribute on `ClaimExtractor`.

Input validation (SAFE-02a) is a pure pre-processing guard at `verify_single_summary()` entry. The duplication check is the only novel algorithm: a set-based ratio is simpler and faster than sliding-window approaches and requires no new imports. Max-claims enforcement (SAFE-02b) is a one-line slice after `identify_medical_claims()` returns. Degraded-mode sidecar (SAFE-03) follows the same file-writing pattern as `_validate_export_safety()` / `_safety_log.json` already in `export_results()`.

**Primary recommendation:** Implement in dependency order — config params first, then seeds JSON, then ClaimExtractor changes (centroid + max-claims), then MedicalVerifier changes (input validation + sidecar write in export_results).

---

## Standard Stack

### Core (already in requirements.txt and confirmed present)

| Library | Version | Purpose | Verified |
|---------|---------|---------|----------|
| `numpy` | 2.4.3 | Centroid computation, embedding arithmetic | [VERIFIED: pip list] |
| `sklearn.metrics.pairwise.cosine_similarity` | (via scikit-learn) | Cosine distance between claim embedding and centroid | [VERIFIED: already imported in claim_extractor_fixed.py line 56] |
| `sentence_transformers.SentenceTransformer` | >=2.2.0 | Encode seed phrases via pubmedbert | [VERIFIED: requirements.txt; already used as self.sentence_model] |
| `json` (stdlib) | — | Load seeds file, write sidecar | [VERIFIED: already used in medical_verifier.py] |
| `datetime` (stdlib) | — | Sidecar timestamp | [VERIFIED: already imported in medical_verifier.py] |
| `pytest` | 9.0.2 | Test runner | [VERIFIED: pip list] |

### No New Dependencies

All required libraries are already installed and imported. Phase 2 introduces zero new `pip install` requirements.

---

## Architecture Patterns

### Pattern 1: Centroid Computation and Cosine Similarity Check

**What:** Encode all seed phrases with `self.sentence_model.encode()`, stack into a matrix, average row-wise to get a centroid, store as `self.danger_centroid`. At check time, call `cosine_similarity(claim_emb.reshape(1,-1), centroid.reshape(1,-1))[0][0]`.

**Why it works:** `get_sentence_embedding()` already returns `np.ndarray` of dtype `float32`. `cosine_similarity` from sklearn operates on 2D arrays — both arguments need `reshape(1,-1)`. This is the identical pattern already used in `calculate_confidence_score()` lines 323-327.

**Exact pattern (from existing code, [VERIFIED: claim_extractor_fixed.py lines 323-327]):**
```python
# Existing pattern — reuse for danger check:
from sklearn.metrics.pairwise import cosine_similarity

claim_emb_2d = claim_embedding.reshape(1, -1)        # shape (1, 768)
centroid_2d = self.danger_centroid.reshape(1, -1)    # shape (1, 768)
similarity = cosine_similarity(claim_emb_2d, centroid_2d)[0][0]  # float

is_semantically_dangerous = similarity > self.config.DANGEROUS_SEMANTIC_THRESHOLD
```

**Centroid computation at init:**
```python
# In ClaimExtractor.__init__(), after self.sentence_model loads:
seeds_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dangerous_guidance_seeds.json')
if os.path.exists(seeds_path):
    try:
        with open(seeds_path, 'r') as f:
            seeds_data = json.load(f)
        all_phrases = [
            phrase
            for phrases in seeds_data.get('categories', {}).values()
            for phrase in phrases
        ]
        seed_embeddings = self.sentence_model.encode(all_phrases, convert_to_numpy=True)
        self.danger_centroid = seed_embeddings.mean(axis=0).astype(np.float32)
        self._seeds_file_status = 'loaded'
        print(f"Danger centroid computed from {len(all_phrases)} seed phrases.")
    except Exception as e:
        print(f"Warning: Could not load seeds file: {e}")
        self.danger_centroid = None
        self._seeds_file_status = 'error'
else:
    print("Warning: dangerous_guidance_seeds.json not found — semantic danger check disabled.")
    self.danger_centroid = None
    self._seeds_file_status = 'missing'
```

**Degraded path:** If `self.sentence_model is None`, `self.danger_centroid` is set to `None` and the semantic check is skipped. Only the existing rule-based check runs.

### Pattern 2: Input Validation at verify_single_summary() Entry

**What:** Pre-processing guard inserted at the top of `verify_single_summary()` before the `self.extractor.extract_claims_from_summary(medical_summary)` call. Returns an early-exit result dict for fatal errors; mutates `medical_summary` and populates `input_validation` dict for soft flags.

**Verified insertion point ([VERIFIED: medical_verifier.py lines 45-63]):**
```python
def verify_single_summary(self, medical_summary: str, summary_id: str = None) -> Dict[str, Any]:
    if not summary_id:
        summary_id = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # --- INPUT VALIDATION (new) ---
    input_validation = {
        'error': None,
        'truncated': False,
        'original_char_count': None,
        'warning': None,
    }

    # Check 1: Non-string type — fatal, return early
    if not isinstance(medical_summary, str):
        input_validation['error'] = 'non_string_input'
        return _make_unknown_result(summary_id, input_validation)

    input_validation['original_char_count'] = len(medical_summary)

    # Check 2: Empty / whitespace — fatal, return early
    if not medical_summary.strip():
        input_validation['error'] = 'empty_input'
        return _make_unknown_result(summary_id, input_validation)

    # Check 3: Oversized — truncate + soft flag
    max_chars = self.global_config.MAX_SUMMARY_CHARS
    if len(medical_summary) > max_chars:
        medical_summary = medical_summary[:max_chars]
        input_validation['truncated'] = True

    # Check 4: High duplication ratio — soft flag
    dup_ratio = _sentence_duplication_ratio(medical_summary)
    if dup_ratio > self.global_config.DUPLICATE_SENTENCE_RATIO:
        input_validation['warning'] = 'repeated_content'

    # ... existing extraction logic below ...
    results = self.extractor.extract_claims_from_summary(medical_summary)
    results['input_validation'] = input_validation
    # ...
```

### Pattern 3: Sentence Duplication Ratio (set-based, no new imports)

**What:** Split text into sentences using `str.split('.')` or existing SpaCy sentences (not available pre-extraction), compute set of unique lowercased stripped sentences, compare set size to total count.

**Best approach for pre-extraction context** — stdlib only, no SpaCy needed here:
```python
def _sentence_duplication_ratio(text: str) -> float:
    """Return the fraction of sentences that are duplicates (0.0 = no dups, 1.0 = all dups)."""
    # Simple split on period — adequate for duplication detection before SpaCy runs.
    sentences = [s.strip().lower() for s in text.split('.') if s.strip()]
    if len(sentences) <= 1:
        return 0.0
    unique = set(sentences)
    duplicate_count = len(sentences) - len(unique)
    return duplicate_count / len(sentences)
```

**Why set-based over sliding window:** The goal is detecting copy-pasted repeated paragraphs in oversized inputs, not near-duplicate detection. Exact set membership is O(n) and requires no dependencies. A ratio of 0.5 (half the sentences are duplicates) is a clear signal of malformed input.

**Why not sliding window:** Sliding window detects near-duplicates in adjacent pairs — appropriate for detecting repetitive AI-generated prose within a paragraph, not malformed input validation. The CONTEXT.md decision is specifically about input shape validation, not prose quality.

### Pattern 4: Max-Claims Enforcement Inside extract_claims_from_summary()

**Verified insertion point ([VERIFIED: claim_extractor_fixed.py lines 762-783]):**
```python
def extract_claims_from_summary(self, medical_summary: str) -> Dict:
    sentences = self.extract_sentences(medical_summary)
    claims = self.identify_medical_claims(sentences)

    # --- MAX-CLAIMS ENFORCEMENT (new, after identify, before embedding validation) ---
    claims_truncated = False
    claims_truncated_count = 0
    max_claims = self.config.MAX_CLAIMS_PER_SUMMARY
    if len(claims) > max_claims:
        claims_truncated_count = len(claims) - max_claims
        claims = claims[:max_claims]         # first-N by document order
        claims_truncated = True

    # Output boundary re-validation (existing — still runs on truncated list)
    for idx, claim in enumerate(claims):
        _validate_claim_schema(claim, context=f"output_boundary[{idx}]")

    return {
        'original_text': medical_summary,
        'sentences': sentences,
        'claims': claims,
        'total_claims': len(claims),
        'claims_truncated': claims_truncated,           # new
        'claims_truncated_count': claims_truncated_count,  # new
    }
```

**Important:** `MAX_CLAIMS_PER_SUMMARY = 50` is already defined in `ConfigurationSettings` at line 77 of medical_config.py [VERIFIED]. No new config field needed for this value — only needs to be read and enforced.

### Pattern 5: Degraded Mode Sidecar in export_results()

**Where sidecar is written:** Inside `export_results()`, after the main JSON/CSV file is written. This mirrors the existing `_validate_export_safety()` / `_safety_log.json` pattern ([VERIFIED: medical_verifier.py lines 811-848]).

**Why export_results() not verify_single_summary():** The sidecar design decision from CONTEXT.md says "written alongside every exported result." The existing `_safety_log.json` is also written in `export_results()`. The sidecar is operational metadata about a run, not a per-call result. Writing it in `export_results()` keeps it co-located with the exported JSON/CSV file.

**Sidecar path formula:**
```python
# In export_results(), after writing main output:
for result in results:
    summary_id = result.get('summary_id', 'unknown')
    sidecar_path = os.path.join(
        os.path.dirname(output_path),
        f"{summary_id}_model_status.json"
    )
    model_status = {
        'summary_id': summary_id,
        'timestamp': datetime.now().isoformat(),
        'degraded_mode': result.get('risk_assessment', {}).get('degraded_mode', False),
        'unavailable_models': (
            ['neuml/pubmedbert-base-embeddings']
            if self.extractor.sentence_model is None else []
        ),
        'fallbacks_used': (
            ['word_count_features']
            if self.extractor.sentence_model is None else []
        ),
        'seeds_file_status': getattr(self.extractor, '_seeds_file_status', 'unknown'),
    }
    with open(sidecar_path, 'w') as f:
        json.dump(model_status, f, indent=2)
```

**degraded_mode flag in result:** Set in `verify_single_summary()` after risk assessment:
```python
if self.extractor.sentence_model is None:
    results['risk_assessment']['degraded_mode'] = True
```

### Pattern 6: Config Params to Add

**[VERIFIED: medical_config.py lines 76-79 confirm MAX_CLAIMS_PER_SUMMARY already exists.]**

New params needed:

| Param | Type | Default | Section to add after |
|-------|------|---------|----------------------|
| `DANGEROUS_SEMANTIC_THRESHOLD` | float | 0.75 | Safety and risk assessment thresholds |
| `MAX_SUMMARY_CHARS` | int | 5000 | Extraction parameters |
| `DUPLICATE_SENTENCE_RATIO` | float | 0.5 | Extraction parameters |

`MAX_CLAIMS_PER_SUMMARY` already exists — no change needed.

**Validation additions needed in `__post_init__`:**
```python
# In the probability checks block:
_check_probability("DANGEROUS_SEMANTIC_THRESHOLD", self.DANGEROUS_SEMANTIC_THRESHOLD)
_check_probability("DUPLICATE_SENTENCE_RATIO", self.DUPLICATE_SENTENCE_RATIO)
# In the positive int block:
_check_positive_int("MAX_SUMMARY_CHARS", self.MAX_SUMMARY_CHARS)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cosine similarity | Custom dot-product / norm formula | `sklearn.metrics.pairwise.cosine_similarity` | Already imported; handles edge cases (zero vector, float precision) |
| Centroid embedding | Manual loop sum | `np.mean(axis=0)` on stacked 2D array | Single numpy operation; numerically stable |
| Encode seed phrases | Tokenize/embed manually | `self.sentence_model.encode(phrases, convert_to_numpy=True)` | Returns correctly normalized float32 array; handles batching |
| JSON sidecar writes | Custom serializer | `json.dump` + `open(..., 'w')` | Matches existing export_results() pattern exactly |
| Test mocking | Real model loads | Extend existing conftest.py mock pattern | conftest.py already mocks spacy, faiss, torch, transformers for fast tests |

---

## Common Pitfalls

### Pitfall 1: Shape Mismatch in Cosine Similarity

**What goes wrong:** `cosine_similarity(a, b)` where `a` or `b` is 1D (shape `(768,)`) raises `ValueError: Expected 2D array`.

**Why it happens:** `SentenceTransformer.encode()` returns shape `(768,)` for a single string. `cosine_similarity` requires shape `(n_samples, n_features)`.

**How to avoid:** Always `reshape(1, -1)` before calling cosine_similarity. This is the existing pattern in `calculate_confidence_score()` — mirror it exactly.

**Warning signs:** `ValueError: Expected 2D array, got 1D array instead` at runtime.

### Pitfall 2: Centroid Computed from Empty Phrases List

**What goes wrong:** If seeds JSON exists but all categories are empty lists, `all_phrases` is `[]`, `sentence_model.encode([])` returns shape `(0, 768)`, and `mean(axis=0)` returns a `(768,)` zero vector — a valid but meaningless centroid that flags everything.

**How to avoid:** Guard before encoding:
```python
if not all_phrases:
    print("Warning: seeds file has no phrases — semantic check disabled.")
    self.danger_centroid = None
    self._seeds_file_status = 'error'
else:
    seed_embeddings = self.sentence_model.encode(all_phrases, convert_to_numpy=True)
    self.danger_centroid = seed_embeddings.mean(axis=0).astype(np.float32)
```

### Pitfall 3: Sidecar Write Fails Silently When outputs/ Doesn't Exist

**What goes wrong:** `open(sidecar_path, 'w')` raises `FileNotFoundError` if the `outputs/` directory was not yet created.

**How to avoid:** Call `os.makedirs(os.path.dirname(sidecar_path), exist_ok=True)` before writing. `export_results()` already does this at line 762 for the main output — the sidecar write must do the same.

### Pitfall 4: Early-Return Result Missing Keys Expected by Downstream

**What goes wrong:** An early-return result (non-string or empty input) skips `_apply_responsible_ai_layer()`, so `results['responsible_ai']` key is absent. Downstream consumers (report_generator, CSV export) crash on missing key.

**How to avoid:** The early-return helper `_make_unknown_result()` must include a complete skeleton of all expected top-level keys:
```python
def _make_unknown_result(summary_id: str, input_validation: dict) -> dict:
    return {
        'summary_id': summary_id,
        'original_text': '',
        'sentences': [],
        'claims': [],
        'total_claims': 0,
        'analysis_timestamp': datetime.now().isoformat(),
        'input_validation': input_validation,
        'risk_assessment': {'level': 'UNKNOWN', 'reason': input_validation['error'], 'stats': {}},
        'responsible_ai': {
            'safety_warnings': [],
            'safety_recommendations': [],
            'requires_expert_review': False,
            'auto_flagged': False,
            'disclaimer': {},
            'safety_assessment': {},
        },
    }
```

### Pitfall 5: MAX_CLAIMS_PER_SUMMARY Already Exists — Don't Duplicate It

**What goes wrong:** Adding a second `MAX_CLAIMS_PER_SUMMARY` field to `ConfigurationSettings` causes a dataclass error or silently overwrites the existing default.

**How to avoid:** [VERIFIED: medical_config.py line 77] `MAX_CLAIMS_PER_SUMMARY: int = 50` already exists. The enforcement code in `extract_claims_from_summary()` only needs to *read* `self.config.MAX_CLAIMS_PER_SUMMARY` — no config change required for this param.

### Pitfall 6: Duplication Ratio Split Produces Empty Strings

**What goes wrong:** `text.split('.')` on a text ending in a period produces a trailing empty string. `len(sentences)` is inflated, making the ratio look higher than it is.

**How to avoid:** Filter in the list comprehension: `[s.strip().lower() for s in text.split('.') if s.strip()]`.

### Pitfall 7: Sidecar Written Per-Result vs Per-File

**What goes wrong:** `export_results()` receives a `List[Dict]`, not a single result. Writing one sidecar for the entire export loses per-result model status detail.

**How to avoid:** Iterate over results in the export loop, one sidecar per result. The sidecar path `outputs/<summary_id>_model_status.json` already encodes the per-result identity via `summary_id`.

---

## Code Examples

### Verified: SentenceTransformer encode returning numpy array
```python
# Source: claim_extractor_fixed.py lines 597-604 [VERIFIED]
def get_sentence_embedding(self, text: str) -> np.ndarray:
    if self.sentence_model is not None:
        embedding = self.sentence_model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
    else:
        # Fallback: word-count features
        return np.array([len(text.split()), text.count('.'), text.count(',')], dtype=np.float32)
```

### Verified: Cosine similarity pattern in existing code
```python
# Source: claim_extractor_fixed.py lines 323-327 [VERIFIED]
claim_emb_2d = claim_embedding.reshape(1, -1)
fact_emb_2d = fact_emb.reshape(1, -1)
cos_sim = cosine_similarity(claim_emb_2d, fact_emb_2d)[0][0]
```

### Verified: Export sidecar pattern (existing _safety_log.json)
```python
# Source: medical_verifier.py lines 844-848 [VERIFIED]
log_path = output_path.replace('.json', '_safety_log.json').replace('.csv', '_safety_log.json')
with open(log_path, 'w') as f:
    json.dump(safety_log, f, indent=2)
```

### Verified: Existing test mock pattern for ClaimExtractor without models
```python
# Source: tests/test_contracts.py lines 66-79 [VERIFIED]
def _make_extractor_no_models(config=None):
    with (
        mock.patch("claim_extractor_fixed.spacy.load", return_value=mock.MagicMock()),
        mock.patch("claim_extractor_fixed.AutoTokenizer.from_pretrained", return_value=mock.MagicMock()),
        mock.patch("claim_extractor_fixed.AutoModel.from_pretrained", return_value=mock.MagicMock()),
        mock.patch.object(ClaimExtractor, "_init_retriever", return_value=None),
    ):
        return ClaimExtractor(config=config)
```

---

## dangerous_guidance_seeds.json — Seed Phrase Design

**File location:** `data/dangerous_guidance_seeds.json` (does not yet exist — [VERIFIED: bash check])

**Schema:**
```json
{
  "version": "1.0",
  "categories": {
    "medication_discontinuation": [ ... ],
    "treatment_avoidance": [ ... ],
    "dangerous_alternatives": [ ... ],
    "emergency_minimization": [ ... ],
    "vaccine_misinformation": [ ... ]
  }
}
```

**Medically grounded seed phrases per category** [ASSUMED — drawn from pharmacovigilance literature patterns; confirm with domain expert if precision-critical]:

- **medication_discontinuation:** "stop taking your insulin", "you can stop warfarin safely", "discontinue your medication without telling your doctor", "wean off antiepileptic drugs yourself", "no need for blood pressure medication", "discontinue statins on your own"

- **treatment_avoidance:** "avoid chemotherapy", "refuse surgery", "do not take antibiotics", "skip your dialysis", "avoid radiation therapy", "decline vaccination", "reject standard treatment"

- **dangerous_alternatives:** "cure cancer with herbs", "heal diabetes with essential oils", "treat infection with crystals", "replace insulin with cinnamon", "use homeopathic remedies for sepsis", "meditation cures meningitis", "prayer heals all disease"

- **emergency_minimization:** "heart attack symptoms are not serious", "stroke can wait until morning", "anaphylaxis will resolve on its own", "you do not need emergency care", "ignore chest pain", "sepsis is manageable at home", "meningitis symptoms are mild"

- **vaccine_misinformation:** "vaccines cause autism", "vaccines contain tracking chips", "vaccines are more dangerous than the disease", "do not vaccinate your children", "natural immunity is always superior", "vaccines destroy immune system"

**Calibration note:** The centroid approach means the exact phrasing matters less than topical density. Including 5-8 diverse phrases per category (40 total) provides adequate centroid coverage. Adding more phrases of the same category shifts the centroid toward that category — balance is important.

**Threshold calibration:** Default `DANGEROUS_SEMANTIC_THRESHOLD = 0.75` is intentionally conservative. In the embedding space of pubmedbert, 0.75 cosine similarity represents high topical similarity. Legitimate clinical discussion of "stopping insulin" (e.g., "patient was counseled not to stop insulin abruptly") should score below 0.75 because the framing is cautionary. Testing against the 13 test summaries already in `test_claim_extraction()` (summaries 8-13 are known dangerous) provides immediate calibration data. [ASSUMED — threshold correctness requires empirical validation with the actual model]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (no pytest.ini detected) |
| Quick run command | `pytest tests/test_safety_guards.py -x -v` |
| Full suite command | `pytest tests/ -x -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-01 | Semantic danger check returns True for seed-like phrases | unit | `pytest tests/test_safety_guards.py::test_semantic_danger_detects_dangerous_phrase -x` | No — Wave 0 |
| SAFE-01 | Semantic danger check returns False for neutral clinical text | unit | `pytest tests/test_safety_guards.py::test_semantic_danger_ignores_safe_phrase -x` | No — Wave 0 |
| SAFE-01 | Rule match OR semantic match triggers flag (either is sufficient) | unit | `pytest tests/test_safety_guards.py::test_danger_flag_triggers_on_rule_match -x` | No — Wave 0 |
| SAFE-01 | Missing seeds file disables semantic check, logs status | unit | `pytest tests/test_safety_guards.py::test_missing_seeds_disables_semantic_check -x` | No — Wave 0 |
| SAFE-02 | Non-string input returns UNKNOWN + error=non_string_input | unit | `pytest tests/test_safety_guards.py::test_input_validation_rejects_non_string -x` | No — Wave 0 |
| SAFE-02 | Empty string returns UNKNOWN + error=empty_input | unit | `pytest tests/test_safety_guards.py::test_input_validation_rejects_empty -x` | No — Wave 0 |
| SAFE-02 | Oversized input is truncated + truncated=True | unit | `pytest tests/test_safety_guards.py::test_input_validation_truncates_oversized -x` | No — Wave 0 |
| SAFE-02 | High duplication ratio sets warning=repeated_content | unit | `pytest tests/test_safety_guards.py::test_input_validation_flags_duplication -x` | No — Wave 0 |
| SAFE-02 | claims_truncated=True when claims exceed MAX_CLAIMS_PER_SUMMARY | unit | `pytest tests/test_safety_guards.py::test_max_claims_truncated_flag -x` | No — Wave 0 |
| SAFE-03 | degraded_mode=True in risk_assessment when sentence_model is None | unit | `pytest tests/test_safety_guards.py::test_degraded_mode_flag_when_model_none -x` | No — Wave 0 |
| SAFE-03 | Sidecar model_status.json written by export_results() | unit | `pytest tests/test_safety_guards.py::test_sidecar_written_on_export -x` | No — Wave 0 |
| SAFE-03 | Sidecar seeds_file_status reflects actual seeds load outcome | unit | `pytest tests/test_safety_guards.py::test_sidecar_seeds_file_status -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_safety_guards.py -x -v`
- **Per wave merge:** `pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_safety_guards.py` — new file covering all 12 test cases above
- [ ] Extend `tests/conftest.py` with fixtures: `mock_verifier_no_models`, `oversized_input`, `duplicate_heavy_input`, `dangerous_claim_text`, `safe_clinical_text`, `seeds_json_path`

**Existing infrastructure is compatible:** `tests/conftest.py` already establishes the mock pattern for heavy dependencies (spacy, faiss, torch, transformers). New tests follow the same `_make_extractor_no_models()` and mock pattern. No new framework setup needed.

**Key fixture design for SAFE-01 tests:** The semantic danger test must mock `self.sentence_model.encode()` to return controlled numpy arrays (known-similar vs known-dissimilar vectors) rather than loading the actual model. This keeps the test fast and deterministic.

```python
# Example fixture pattern for SAFE-01 unit test:
def _make_extractor_with_mock_centroid(config, centroid_vec):
    with (
        mock.patch("claim_extractor_fixed.spacy.load", return_value=mock.MagicMock()),
        mock.patch.object(ClaimExtractor, "_init_retriever", return_value=None),
    ):
        extractor = ClaimExtractor.__new__(ClaimExtractor)
        extractor.config = config
        extractor.sentence_model = mock.MagicMock()
        extractor.danger_centroid = centroid_vec
        extractor._seeds_file_status = 'loaded'
        return extractor
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | All | Yes | 3.13.11 | — |
| numpy | Centroid computation | Yes | 2.4.3 | — |
| pytest | Test runner | Yes | 9.0.2 | — |
| sentence-transformers | Seed encoding | [ASSUMED: in requirements.txt] | >=2.2.0 | — |
| scikit-learn | cosine_similarity | [ASSUMED: in requirements.txt] | >=1.1.0 | — |
| json (stdlib) | Seeds file + sidecar | Yes | stdlib | — |
| os (stdlib) | Path manipulation | Yes | stdlib | — |

**Note:** `pip list` only returned numpy and pytest in the test environment. The remaining packages are declared in requirements.txt but their install status could not be verified via pip list in this session. This does not block planning — the existing code imports them successfully in production.

**Missing dependencies with no fallback:** None identified.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Yes | Input validation at verify_single_summary() entry; type + size + duplication checks |
| V6 Cryptography | No | — |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Oversized input causing memory exhaustion | Denial of Service | `MAX_SUMMARY_CHARS` truncation before ClaimExtractor runs |
| Malformed input causing unhandled exception | Denial of Service | Non-string and empty checks return early before any processing |
| Repeated content inflating claim counts | Tampering (misleading risk scores) | Duplication ratio flag surfaces the anomaly |
| Model unavailability silently degrading safety detection | Elevation of Privilege (false safety) | `degraded_mode` flag and sidecar make unavailability explicit |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Seed phrases listed for each category are medically representative | dangerous_guidance_seeds.json design | Centroid may not cover real dangerous guidance patterns — calibrate empirically with the 13 test summaries |
| A2 | DANGEROUS_SEMANTIC_THRESHOLD = 0.75 produces acceptable precision/recall | Architecture Patterns / Pitfalls | Too high = misses dangerous content; too low = flags legitimate clinical discussion of the same topics |
| A3 | sentence-transformers and scikit-learn are installed in the runtime environment | Environment Availability | Tests that mock these pass; live pipeline would fail at import time |

---

## Open Questions (RESOLVED)

1. **Where does the "no entities detected" warning get set?** — **RESOLVED** (plan 02-03 Task 4 + plan 02-04 Task 2)
   - What we know: CONTEXT.md says this is "post-NER, inside extractor" — not a pre-validation stop
   - What's unclear: `identify_medical_claims()` already tracks `medical_entities` per claim; but there is no existing path to propagate a "no entities in entire summary" signal back to `input_validation`
   - Recommendation: In `extract_claims_from_summary()`, after `claims = self.identify_medical_claims(sentences)`, check `if not any(c['medical_entities'] for c in claims)` and return a `no_entities_detected` flag alongside the result dict. `verify_single_summary()` then sets `input_validation['warning'] = 'no_entities_detected'` if the flag is present. This avoids adding a new argument to the extractor's public API.
   - **RESOLVED:** Implemented exactly as recommended. Plan 02-03 Task 4 adds `no_entities` key to the extract_claims_from_summary() return dict (after max-claims truncation). Plan 02-04 Task 2 reads `results.get('no_entities')` post-extraction and sets `input_validation['warning'] = 'no_entities_detected'` when no prior warning is present. Test stub `test_input_validation_warns_no_entities` added in plan 02-01 Task 3 and tracked as row 02-02-05 in 02-VALIDATION.md.

2. **Does the sidecar write belong in export_results() or verify_single_summary()?** — **RESOLVED** (plan 02-05)
   - What we know: CONTEXT.md says "written alongside every exported result (always, not just on degradation)." The sidecar path is `outputs/<id>_model_status.json`. The existing `_safety_log.json` is written in `export_results()`.
   - What's unclear: `verify_single_summary()` does not know the output path; `export_results()` does. Writing in export_results() means the sidecar only exists after export, not after every verification call.
   - Recommendation: Write in `export_results()` — this matches the existing `_safety_log.json` pattern, keeps output artifacts co-located, and aligns with "alongside every exported result" wording. Verified as the correct interpretation.
   - **RESOLVED:** Implemented in plan 02-05 (Wave 3) — sidecar written inside `export_results()` per-result, covered by `test_sidecar_written_on_export` and `test_sidecar_seeds_file_status`.

---

## Sources

### Primary (HIGH confidence)
- `src/claim_extractor_fixed.py` — all ClaimExtractor patterns, SentenceTransformer encode, cosine_similarity usage, existing mock pattern
- `src/medical_verifier.py` — verify_single_summary(), export_results(), _validate_export_safety(), dangerous_terms dict
- `src/medical_config.py` — ConfigurationSettings fields, __post_init__ validation pattern, accessor methods
- `tests/conftest.py` — mock infrastructure, fixture pattern, heavy dependency patching
- `tests/test_contracts.py` — _make_extractor_no_models() pattern
- `requirements.txt` — declared dependencies and minimum versions

### Secondary (MEDIUM confidence)
- CONTEXT.md Phase 2 decisions — all locked decisions reproduced verbatim

### Tertiary (LOW confidence)
- Seed phrase content per category [ASSUMED from pharmacovigilance literature patterns in training data — not verified against published pharmacovigilance guidelines in this session]
- DANGEROUS_SEMANTIC_THRESHOLD = 0.75 effectiveness [ASSUMED — requires empirical testing]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in codebase imports or requirements.txt
- Architecture: HIGH — all patterns extracted directly from existing code (insertion points identified by line number)
- Config changes: HIGH — MAX_CLAIMS_PER_SUMMARY already exists; three new params follow established __post_init__ validation pattern exactly
- Seed phrases: LOW — content is assumed from training knowledge; domain expert review recommended before production use
- Threshold value (0.75): LOW — requires empirical testing against the 13 known-dangerous test summaries in test_claim_extraction()

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable Python/numpy stack; no fast-moving dependencies)
