---
phase: 04-reproducibility-and-runtime-ops
reviewed: 2026-05-01T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/medical_preprocessor.py
  - src/claim_extractor_fixed.py
  - tests/conftest.py
  - tests/test_kb_metadata.py
findings:
  critical: 4
  warning: 5
  info: 3
  total: 12
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-05-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files were reviewed covering the Phase 4 DATA-01 (KB metadata write) and DATA-02 (FAISS
persistence) tracks, plus the test infrastructure that validates them.

The metadata write logic in `medical_preprocessor.py` contains a fatal design flaw: it checks
for `kb_embeddings_preprocessed.npy` but the preprocessor never actually writes that file,
so `_write_kb_metadata` raises `FileNotFoundError` on every fresh pipeline run. Additionally,
the file contains a dead code block after a `return` statement that will never execute.

In `claim_extractor_fixed.py` the `identify_medical_claims` method calls `.ents` on a
HuggingFace pipeline result (which returns a plain list, not a spaCy Doc), causing an
`AttributeError` crash on every non-empty sentence. A separate boolean logic inversion in the
`rule_danger_match` field and a leftover debug `print` block are also present.

`tests/conftest.py` contains a logic error in a fixture helper that silently produces
unexpected test behaviour.

---

## Critical Issues

### CR-01: `_write_kb_metadata` always raises `FileNotFoundError` — embeddings file is never written by the preprocessor

**File:** `src/medical_preprocessor.py:787-789`
**Issue:** `preprocess_knowledge_base` constructs `embeddings_path` as
`data/kb_embeddings_preprocessed.npy` and passes it to `_write_kb_metadata`, which
immediately raises `FileNotFoundError` when the file does not exist (lines 803-807).
`medical_preprocessor.py` contains no `np.save` call anywhere in its source; the embeddings
are computed solely during `advanced_semantic_deduplication` and held in memory. The `.npy`
file is only written by `claim_extractor_fixed.py` (as a by-product of the claim-extraction
phase), which runs *after* preprocessing. Therefore on every fresh pipeline run — the exact
scenario DATA-01 is designed for — the final metadata write is unreachable.

**Fix:** Either (a) save the embeddings inside `preprocess_knowledge_base` immediately after
`advanced_semantic_deduplication` returns, then call `_write_kb_metadata`:

```python
# After advanced_semantic_deduplication returns df:
embeddings_path = os.path.join(os.path.dirname(output_path), 'kb_embeddings_preprocessed.npy')
if self._last_embeddings is not None:          # store during deduplication
    np.save(embeddings_path, self._last_embeddings)

# ... save CSV ...
self._write_kb_metadata(output_path, embeddings_path, final_df)
```

Or (b) make `_write_kb_metadata` optional on the embeddings artifact and skip the
`embeddings_sha256` field when the file is absent, documenting the limitation.

---

### CR-02: `AttributeError` crash — HuggingFace pipeline result treated as spaCy Doc

**File:** `src/claim_extractor_fixed.py:857-865`
**Issue:** `self.ner_nlp` is a HuggingFace `pipeline` (token-classification), which returns a
plain Python `list` of dicts when called. Line 857 calls `ner_doc = self.ner_nlp(sentence)`
and line 859 then accesses `ner_doc.ents` — an attribute that does not exist on a `list`.
Every call to `identify_medical_claims` that processes a non-empty sentence will crash with:

```
AttributeError: 'list' object has no attribute 'ents'
```

This is a BLOCKER: the entire claim-extraction pipeline is non-functional.

**Fix:** Iterate over the list directly and read the `word`, `entity_group`, `start`, `end`
keys that `aggregation_strategy="simple"` produces:

```python
ner_results = self.ner_nlp(sentence)   # returns List[dict]
medical_entities = []
for ent in ner_results:
    medical_entities.append({
        'text': ent['word'],
        'label': ent.get('entity_group', 'ENTITY'),
        'start': ent.get('start', 0),
        'end': ent.get('end', 0),
    })
```

---

### CR-03: Dead code after `return` — `_resolve_duplicate_pairs` has unreachable statement

**File:** `src/medical_preprocessor.py:668-670`
**Issue:** After the `return to_remove` statement at line 668, line 670 contains:

```python
        return df_deduplicated.reset_index(drop=True)
```

This line is unreachable and references `df_deduplicated`, a variable that does not exist in
the scope of `_resolve_duplicate_pairs`. If Python ever reached it (e.g., through a refactor
that removes the prior `return`), it would raise `NameError`. The block appears to be a paste
residue from `advanced_semantic_deduplication`.

**Fix:** Remove lines 669-670 entirely.

---

### CR-04: `rule_danger_match` boolean logic is inverted — always `False` when semantic danger is detected

**File:** `src/claim_extractor_fixed.py:949-950`
**Issue:** The intent of the SAFE-01 hybrid check is to distinguish whether the dangerous flag
was triggered by rule-based matching versus semantic centroid matching. The assignment sequence
is:

```python
# line 949
claim['is_dangerous'] = bool(claim.get('is_dangerous', False) or semantic_match)
# line 950
claim['rule_danger_match'] = bool(claim.get('is_dangerous', False)) and not bool(semantic_match)
```

At line 950, `claim.get('is_dangerous', False)` reads the value that was just written at
line 949. If `semantic_match` is `True`, then `is_dangerous` is `True` AND `not semantic_match`
is `False`, so `rule_danger_match` is `False` — even though a rule might also have fired.
If a rule had fired (`is_dangerous` was `True` before line 949) and `semantic_match` is also
`True`, `rule_danger_match` is still `False`. The field is therefore unreliable as a
diagnostic signal. Downstream consumers of `rule_danger_match` will silently receive incorrect
data.

**Fix:** Capture the pre-merge rule flag before overwriting `is_dangerous`:

```python
rule_fired = bool(claim.get('is_dangerous', False))
semantic_match = self.is_semantically_dangerous(claim.get('claim_text', ''))
claim['semantic_danger_match'] = bool(semantic_match)
claim['is_dangerous'] = bool(rule_fired or semantic_match)
claim['rule_danger_match'] = rule_fired
```

---

## Warnings

### WR-01: Hardcoded `current_year = 2025` will silently produce wrong recency scores

**File:** `src/medical_preprocessor.py:439`
**Issue:** `grade_evidence_quality` computes `years_old = current_year - publication_year`
using a hardcoded literal `2025`. As of 2026-05-01 (the current date), research from 2023–2025
will receive an inflated `+0.1` or `+0.2` recency bonus; 2024–2025 papers will be classified
as "very recent". This error silently degrades evidence grading without any visible failure.

**Fix:** Replace the literal with a dynamic value:

```python
from datetime import date
current_year = date.today().year
```

---

### WR-02: `preprocess_knowledge_base` crashes with `ValueError` when all `publication_year` values are NaN

**File:** `src/medical_preprocessor.py:693`
**Issue:** Line 693 formats the year range:

```python
print(f"   Year range: {df['publication_year'].min():.0f} - {df['publication_year'].max():.0f}")
```

When all rows fail `pd.to_numeric` conversion, both `.min()` and `.max()` return `nan`. In
Python 3.12+ (and some 3.11 builds), formatting `float('nan')` with `:.0f` raises
`ValueError: Cannot convert nan to integer`. The pipeline would crash before any processing
occurs, despite this being a purely cosmetic print statement.

**Fix:**

```python
yr_min = df['publication_year'].min()
yr_max = df['publication_year'].max()
yr_range = (
    f"{yr_min:.0f} - {yr_max:.0f}"
    if pd.notna(yr_min) and pd.notna(yr_max)
    else "unknown"
)
print(f"   Year range: {yr_range}")
```

---

### WR-03: Negation/uncertainty detection reads *supporting fact* flags instead of the claim sentence itself

**File:** `src/claim_extractor_fixed.py:908-917`
**Issue:** Lines 908-909 determine `has_negation` and `has_uncertainty` by checking whether
*any of the top-3 retrieved KB facts* carry those flags:

```python
has_negation   = any(fact.get('has_negation', False) for fact in supporting_facts[:3]) ...
has_uncertainty = any(fact.get('has_uncertainty', False) for fact in supporting_facts[:3]) ...
```

These flags come from preprocessing of the *knowledge base*, not the input sentence. A claim
like "Patient was not prescribed aspirin" could match KB facts that themselves contain no
negation and therefore `has_negation` would be `False` — the exact opposite of correct. The
fallback (lines 912-917) only fires when `'has_negation'` is absent from the facts entirely,
not when the claim's own negation contradicts the facts' negation status. This logic means
negation signals from the input text can be silently suppressed.

**Fix:** Always run the fallback negation/uncertainty scan on the claim sentence itself and
combine it with any signal from supporting facts:

```python
text_lower = sentence.lower()
negation_words  = ['not', 'no', 'never', 'none', 'without', 'absent', 'lacks', 'denies']
uncertainty_words = ['maybe', 'perhaps', 'possibly', 'might', 'may', 'could', 'suspicious', 'suggestive']
claim_has_negation    = any(w in text_lower for w in negation_words)
claim_has_uncertainty = any(w in text_lower for w in uncertainty_words)
has_negation    = claim_has_negation or any(f.get('has_negation', False)    for f in supporting_facts[:3])
has_uncertainty = claim_has_uncertainty or any(f.get('has_uncertainty', False) for f in supporting_facts[:3])
```

---

### WR-04: `conftest.py` helper `_make_invalid_claim_missing_claim_text` silently loses the original `claim_text` value

**File:** `tests/conftest.py:82-87`
**Issue:** The helper is documented as "return a claim that uses the legacy `text` key instead
of `claim_text`", implying the original text value should be preserved. The implementation is:

```python
del claim["claim_text"]
claim["text"] = claim.get("claim_text", "some legacy text")  # key was just deleted
```

Because `claim_text` is deleted on line 85 before the `.get()` call on line 86, `.get()`
always falls back to `"some legacy text"` and never carries the original text value across.
Any test that relies on the content of `claim["text"]` matching the original claim text will
silently operate on incorrect data.

**Fix:**

```python
original_text = claim.pop("claim_text")
claim["text"] = original_text
```

---

### WR-05: `_find_duplicates_faiss` and `_find_duplicates_batch` have mismatched default thresholds

**File:** `src/medical_preprocessor.py:593`, `src/medical_preprocessor.py:619`
**Issue:** Both private methods have a default `threshold=0.70`, but the public caller
`advanced_semantic_deduplication` uses `similarity_threshold=0.87`. The mismatch only matters
if either method is called directly (e.g., in future tests or sub-pipelines), but the
inconsistency makes the code fragile and misleading. The method signatures advertise a
threshold of `0.70` while the intended operating point is `0.87`.

**Fix:** Change both default values to match the intended operating threshold:

```python
def _find_duplicates_faiss(self, embeddings, threshold=0.87, k=20):
def _find_duplicates_batch(self, embeddings, threshold=0.87, batch_size=500):
```

---

## Info

### IN-01: Left-over debug `print` block in `calculate_confidence_score`

**File:** `src/claim_extractor_fixed.py:540-550`
**Issue:** A debug block gated on `composite_score <= 0.1` (comment reads "DEBUG: Print when
score becomes 0 or very low") prints internal scoring components to stdout. This fires on
every low-confidence claim in production, polluting pipeline output and potentially exposing
sensitive claim text.

**Fix:** Remove the block entirely, or replace it with a `logging.debug(...)` call so it is
silenced by default in production.

---

### IN-02: `test_preprocess_knowledge_base_calls_write_metadata` uses source inspection instead of a behavioral assertion

**File:** `tests/test_kb_metadata.py:291-296`
**Issue:** The test uses `inspect.getsource()` to check that the string `'_write_kb_metadata'`
appears in the source of `preprocess_knowledge_base`. This is a fragile static check: it
passes even if the call is in a comment, a docstring, or a disabled code path. It will not
detect regressions where the method is renamed or the call is accidentally removed from the
active code path.

**Fix:** Replace with a behavioral mock assertion:

```python
def test_preprocess_knowledge_base_calls_write_metadata(self, tmp_path):
    mp = _make_preprocessor()
    with mock.patch.object(mp, '_write_kb_metadata', return_value=str(tmp_path / 'kb_metadata.json')) as m:
        # ... set up minimal CSV and call preprocess_knowledge_base ...
        m.assert_called_once()
```

---

### IN-03: `_generate_preprocessing_report` silently swallows all exceptions

**File:** `src/medical_preprocessor.py:878`
**Issue:** The entire report-generation body is wrapped in a bare `except Exception as e: print(...)`.
While the report is auxiliary, a silent failure here means a corrupted or partially written
report file is never surfaced. A disk-full error or a permission error would be swallowed
identically.

**Fix:** At minimum, re-raise `OSError`/`PermissionError` that indicate persistent storage
problems, and only swallow transient or expected failures (e.g., missing optional columns).

---

_Reviewed: 2026-05-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
