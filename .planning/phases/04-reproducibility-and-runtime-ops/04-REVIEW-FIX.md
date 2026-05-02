---
phase: 04-reproducibility-and-runtime-ops
fixed_at: 2026-05-01T00:00:00Z
review_path: .planning/phases/04-reproducibility-and-runtime-ops/04-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-05-01T00:00:00Z
**Source review:** .planning/phases/04-reproducibility-and-runtime-ops/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (4 Critical, 5 Warning)
- Fixed: 9
- Skipped: 0

## Fixed Issues

### CR-01: `_write_kb_metadata` always raises `FileNotFoundError` — embeddings file is never written by the preprocessor

**Files modified:** `src/medical_preprocessor.py`
**Commit:** 6f7427d
**Applied fix:** Replaced the blanket `FileNotFoundError` guard on both artifacts with a mandatory check for the CSV only. The embeddings file is now optional: `embeddings_present = os.path.exists(embeddings_path)` is computed and `embeddings_sha256` in the metadata dict is set to the file's SHA-256 when present, or `None` when absent. This unblocks fresh pipeline runs where the `.npy` file is produced by the later `claim_extractor_fixed.py` stage.

---

### CR-02: `AttributeError` crash — HuggingFace pipeline result treated as spaCy Doc

**Files modified:** `src/claim_extractor_fixed.py`
**Commit:** e7d8b6d
**Applied fix:** Replaced `ner_doc = self.ner_nlp(sentence)` / `for ent in ner_doc.ents` with `ner_results = self.ner_nlp(sentence)` / `for ent in ner_results`, reading `ent['word']`, `ent.get('entity_group', 'ENTITY')`, `ent.get('start', 0)`, `ent.get('end', 0)` from the HuggingFace `List[dict]` result rather than attempting `.ents` on the list.

---

### CR-03: Dead code after `return` — `_resolve_duplicate_pairs` has unreachable statement

**Files modified:** `src/medical_preprocessor.py`
**Commit:** fe59e44
**Applied fix:** Removed the two unreachable lines (`return df_deduplicated.reset_index(drop=True)` and the blank line preceding it) that appeared after the valid `return to_remove` statement in `_resolve_duplicate_pairs`.

---

### CR-04: `rule_danger_match` boolean logic is inverted — always `False` when semantic danger is detected

**Files modified:** `src/claim_extractor_fixed.py`
**Commit:** a48451d
**Applied fix:** Captured the pre-merge rule flag as `rule_fired = bool(claim.get('is_dangerous', False))` before calling `is_semantically_dangerous`. Then set `claim['is_dangerous'] = bool(rule_fired or semantic_match)` and `claim['rule_danger_match'] = rule_fired`. This ensures `rule_danger_match` reflects whether the rule-based path fired independently of the semantic check.
**Note:** This is a logic fix; requires human verification that the corrected semantics match the intended downstream behaviour.

---

### WR-01: Hardcoded `current_year = 2025` will silently produce wrong recency scores

**Files modified:** `src/medical_preprocessor.py`
**Commit:** 0d18964
**Applied fix:** Replaced `current_year = 2025  # Current year` with `current_year = datetime.today().year`. The `datetime` class is already imported at the top of the module, so no additional import was needed.

---

### WR-02: `preprocess_knowledge_base` crashes with `ValueError` when all `publication_year` values are NaN

**Files modified:** `src/medical_preprocessor.py`
**Commit:** cf1e78a
**Applied fix:** Extracted `yr_min` and `yr_max`, then conditionally formats the range string as `f"{yr_min:.0f} - {yr_max:.0f}"` only when both values satisfy `pd.notna()`, falling back to `"unknown"` otherwise.

---

### WR-03: Negation/uncertainty detection reads *supporting fact* flags instead of the claim sentence itself

**Files modified:** `src/claim_extractor_fixed.py`
**Commit:** 0d55ac4
**Applied fix:** Removed the KB-facts-only primary check and the conditional fallback. Replaced both with an unconditional scan of `sentence.lower()` against `negation_words` / `uncertainty_words`, then combined with any flags present on `supporting_facts[:3]` via `or`. The claim sentence is now always the primary source of truth for negation/uncertainty signals.

---

### WR-04: `conftest.py` helper `_make_invalid_claim_missing_claim_text` silently loses the original `claim_text` value

**Files modified:** `tests/conftest.py`
**Commit:** 05e04d2
**Applied fix:** Replaced the `del` + `claim.get("claim_text", ...)` pattern (which always fell back because the key was already deleted) with `original_text = claim.pop("claim_text")` followed by `claim["text"] = original_text`, correctly preserving the original text value.

---

### WR-05: `_find_duplicates_faiss` and `_find_duplicates_batch` have mismatched default thresholds

**Files modified:** `src/medical_preprocessor.py`
**Commit:** d0340c3
**Applied fix:** Changed both method signatures from `threshold=0.70` to `threshold=0.87`, matching the operating threshold used by the public caller `advanced_semantic_deduplication`.

---

_Fixed: 2026-05-01T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
