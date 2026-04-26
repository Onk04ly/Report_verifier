# Phase 3: Regression Safety Net - Research

**Researched:** 2026-04-26
**Domain:** Python/pytest test authoring for safety-critical medical AI logic
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Create two new test files: `tests/test_risk_assessment.py` (TEST-01 + TEST-02) and `tests/test_confidence_scoring.py` (TEST-03). Do not extend existing test files.
- **D-02:** Use both direct unit tests AND integration smoke tests for `_assess_overall_risk()`.
  - Unit path: `MedicalVerifier.__new__()` shell + inject `risk_thresholds` and `safety_config` from `get_global_config()`. Feed minimal claim dicts directly. Covers Layer 4 threshold math precisely.
  - Integration path: Use `mock_verifier_no_models` fixture (already in conftest.py) + feed crafted text strings via `verify_single_summary()`. Covers Layer 1 implausibility triggers.
- **D-03:** Integration smoke tests assert `result['risk_assessment']['level']` only — not the `reason` string or sub-fields. Stable against reason formatting changes.
- **D-04:** Layer 4 threshold boundary tests derive claim counts dynamically from `get_global_config()` (e.g., `int(threshold * N)` to hit exact boundary). Never hardcode threshold values (0.60, 0.40, 0.70) in test fixtures — thresholds must be sourced from config exactly as production code does.
- **D-05:** Test each of the 5 detection methods directly via `MedicalVerifier.__new__()` and `ClaimExtractor.__new__()` shell injection. Methods under test:
  - `MedicalVerifier._analyze_medical_impossibilities()`
  - `MedicalVerifier._analyze_patient_safety_risks()`
  - `MedicalVerifier._analyze_evidence_contradictions()`
  - `ClaimExtractor._check_biological_impossibilities_optimized()`
  - `ClaimExtractor._check_evidence_based_violations_optimized()`
- **D-06:** 1-2 canonical trigger strings per method: one positive trigger (expect non-empty issues list) and one negative (safe clinical text, expect empty list). No per-family exhaustive coverage in Phase 3.
- **D-07:** Dangerous-term detection tests go into `tests/test_risk_assessment.py` (same file as TEST-01, different TestClass).
- **D-08:** Mock `ClaimExtractor.get_sentence_embedding()` to return fixed deterministic numpy arrays. Do NOT use sklearn `cosine_similarity` — it is mocked as MagicMock in test env. Implement cosine comparison via numpy dot product in test setup if needed.
- **D-09:** Assert `(label, score)` return: label is `'HIGH'`/`'MEDIUM'`/`'LOW'` and numeric score is in `[0.0, 1.0]`. No exact float assertions.
- **D-10:** Two fixture cases minimum: high-similarity supporting facts (expect `'HIGH'`) and low-similarity/absent facts (expect `'LOW'`).

### Claude's Discretion

- Internal TestClass naming, exact fixture variable names, and which specific canonical trigger strings to use can follow existing conventions from `test_safety_guards.py` and `test_contracts.py`.
- Number of integration smoke test cases (known-good + known-bad summaries) is Claude's call — 2-4 is sufficient.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-01 | Automated tests verify four-layer risk transitions and threshold boundaries | `_assess_overall_risk()` Layer 1-4 logic fully mapped; config-sourced threshold boundaries identified; both unit and integration paths confirmed viable |
| TEST-02 | Automated tests verify dangerous-term and evidence-violation detection behavior | All 5 target methods read and their trigger conditions documented; canonical positive/negative trigger strings identified |
| TEST-03 | Automated tests cover confidence score computation and regression-sensitive constants | `calculate_confidence_score()` full flow read; mock injection pattern confirmed; numpy-only cosine approach viable |
</phase_requirements>

---

## Summary

Phase 3 adds two new test files that cover the three safety-critical logic areas without changing any production code. All required source methods have been read in full. The codebase already has a working pytest 9.0.2 suite (47 tests, 5.11 s) and an established pattern — `Class.__new__()` shell injection to bypass `__init__` and avoid model loading — demonstrated in `tests/test_safety_guards.py` and `tests/test_contracts.py`.

The core challenge is `calculate_confidence_score()` in TEST-03: the production method calls `sklearn.metrics.pairwise.cosine_similarity`, which conftest.py mocks to a `MagicMock`, making its return value non-numeric. Tests must re-implement cosine similarity using `numpy` dot product inside their setup, then inject pre-computed supporting fact embeddings so the method's internal similarity loop calls `get_sentence_embedding()` (which will be mocked) and then calls `cosine_similarity` (mocked). The decision (D-08) is to patch `cosine_similarity` at the test level with a numpy-based replacement rather than relying on the globally mocked version.

For TEST-01's Layer 4 threshold boundary logic, the relevant thresholds are `HIGH_RISK_LOW_CONF_RATIO = 0.50`, `MEDIUM_RISK_LOW_CONF_RATIO = 0.30`, and `LOW_RISK_HIGH_CONF_RATIO = 0.40`, but tests must read these from `get_global_config()` at runtime, not hardcode them.

**Primary recommendation:** Use the `ClaimExtractor.__new__()` and `MedicalVerifier.__new__()` shell injection pattern throughout; resolve the `cosine_similarity` mock conflict by patching `claim_extractor_fixed.cosine_similarity` at the test level using `unittest.mock.patch`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test runner and fixture system | Already installed; used by all existing test files [VERIFIED: pytest --version] |
| numpy | (project dep) | Deterministic embedding arrays + cosine math | Already used in conftest.py and test_safety_guards.py; pure-numpy cosine avoids mocked sklearn [VERIFIED: tests/conftest.py imports] |
| unittest.mock | stdlib | Shell injection, patch, MagicMock | Established pattern in all existing test files [VERIFIED: tests/test_safety_guards.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| importlib.util | stdlib | Load src/ modules without package install | Used in test_contracts.py — use same pattern if module reload is needed |
| pathlib | stdlib | Cross-platform src path resolution | Established in test_contracts.py |

**Installation:** No new dependencies. All required libraries are already available.

**Run command:** [VERIFIED: baseline passing]
```bash
pytest tests/ -x -v
```

---

## Architecture Patterns

### Recommended Project Structure

```
tests/
├── conftest.py                    # existing — shared fixtures, heavy dep mocks
├── test_contracts.py              # existing — Phase 1 schema/config tests
├── test_safety_guards.py          # existing — Phase 2 SAFE-01/02/03 tests
├── test_risk_assessment.py        # NEW — TEST-01 (risk layers) + TEST-02 (danger detection)
└── test_confidence_scoring.py     # NEW — TEST-03 (confidence score)
```

### Pattern 1: Shell Injection for MedicalVerifier Unit Tests (TEST-01, TEST-02)

**What:** Bypass `MedicalVerifier.__init__()` (which loads heavy models) using `__new__()`, then manually set only the attributes the method under test reads.

**When to use:** Any test targeting `_assess_overall_risk()`, `_analyze_medical_impossibilities()`, `_analyze_patient_safety_risks()`, or `_analyze_evidence_contradictions()`.

**Required attributes for `_assess_overall_risk()`:**
- `self.risk_thresholds` — from `get_global_config().get_risk_thresholds()`
- `self.safety_config` — from `get_global_config().get_safety_config()`
- (Layer 1 calls `_detect_medical_implausibility()` which calls `_analyze_*` and `_check_evidence_based_validity()` — no additional attributes needed for these sub-methods, they are pure text analysis)

**Required attributes for `_analyze_*()` methods:** None beyond the instance itself — all three methods only use `claim_text` parameter and local pattern lookups. [VERIFIED: src/medical_verifier.py lines 214-296]

**Example:**
```python
# Source: tests/test_safety_guards.py + src/medical_verifier.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from medical_verifier import MedicalVerifier
from medical_config import get_global_config

def _make_verifier_shell():
    cfg = get_global_config()
    v = MedicalVerifier.__new__(MedicalVerifier)
    v.risk_thresholds = cfg.get_risk_thresholds()
    v.safety_config = cfg.get_safety_config()
    return v
```

### Pattern 2: Shell Injection for ClaimExtractor Penalty Methods (TEST-02)

**What:** `_check_biological_impossibilities_optimized()` and `_check_evidence_based_violations_optimized()` require only `self.config` (for penalty constants) and no model instances.

**Required attributes:**
- `self.config` — from `get_global_config()`
- No `sentence_model`, no `faiss_index`, no `kb` needed

**Call signature:**
```python
# Source: src/claim_extractor_fixed.py lines 494-532
# Both methods take (self, text_lower: str, entity_set: set) -> float
penalty = extractor._check_biological_impossibilities_optimized(text.lower(), set())
penalty = extractor._check_evidence_based_violations_optimized(text.lower(), set())
```

**Note on return type:** Both methods return a `float` penalty (0.0 = no violation, up to 1.0 = critical). They do NOT return an issues list. The issues-list interface belongs to `MedicalVerifier._analyze_*()`. Tests for these penalty methods should assert `penalty > 0` (positive trigger) or `penalty == 0.0` (negative). [VERIFIED: src/claim_extractor_fixed.py lines 494-532]

### Pattern 3: Layer 4 Threshold Boundary Construction (TEST-01 unit path)

**What:** Build claim lists with exact counts that cross Layer 4 thresholds, deriving counts from config.

**How:** [VERIFIED: src/medical_verifier.py lines 595-648]
```python
cfg = get_global_config()
rt = cfg.get_risk_thresholds()
N = 10  # total claims in fixture

# HIGH_RISK boundary: low_conf_ratio >= high_risk_low_conf_ratio (0.50)
high_risk_low_count = int(rt['high_risk_low_conf_ratio'] * N)  # = 5
# Build N claims with exactly high_risk_low_count LOW confidence
```

**Claim dict minimum schema for `_assess_overall_risk()`:** [VERIFIED: src/medical_verifier.py line 84 + conftest.py]
```python
{
    'claim_text': str,           # required by _validate_verifier_claim_schema
    'verification_confidence': 'HIGH' | 'MEDIUM' | 'LOW',
    'verification_score': float,
}
```
Optional keys used in Layer 4: `has_negation` (bool), `has_uncertainty` (bool) — default to False if absent.

### Pattern 4: Cosine Similarity Mock Resolution (TEST-03)

**What:** conftest.py globally mocks `sklearn.metrics.pairwise` as a MagicMock. `calculate_confidence_score()` imports `cosine_similarity` from that module at file load time, making it a MagicMock returning a MagicMock — not a float.

**Solution:** Patch `claim_extractor_fixed.cosine_similarity` at the test level with a real numpy implementation before calling `calculate_confidence_score()`.

```python
# Source: Pattern derived from test_contracts.py + src/claim_extractor_fixed.py lines 364-370
import numpy as np
import unittest.mock as mock

def _np_cosine_sim(a, b):
    """Replacement that returns a shape-(1,1) array like sklearn does."""
    a_flat = a.flatten()
    b_flat = b.flatten()
    denom = np.linalg.norm(a_flat) * np.linalg.norm(b_flat)
    val = float(np.dot(a_flat, b_flat) / denom) if denom > 0 else 0.0
    return np.array([[val]])

# In test body:
import claim_extractor_fixed
with mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim):
    label, score = extractor.calculate_confidence_score(claim_text, supporting_facts)
```

**Supporting fact dict schema required by `calculate_confidence_score()`:** [VERIFIED: src/claim_extractor_fixed.py lines 350-358]
```python
{
    'text': str,              # used to call get_sentence_embedding(fact['text'])
    'distance': float,        # used for outlier/distance penalty
    'quality_score': float,   # defaults to 0.5 if missing
    'evidence_grade': str,    # 'A'/'B'/'C'/'D'; defaults to 'C' if missing
    'confidence_modifier': float,  # defaults to 1.0 if missing
}
```

**get_sentence_embedding mock:** Must be patched on the extractor instance to return fixed numpy arrays of shape `(768,)` or any consistent shape.

### Pattern 5: Integration Smoke Tests via mock_verifier_no_models (TEST-01)

**What:** Feed canonical text strings to `mock_verifier_no_models.verify_single_summary()` and assert only on `result['risk_assessment']['level']`.

**Fixture already in conftest.py:** `mock_verifier_no_models` — patches `SentenceTransformer` → None, patches `ClaimExtractor._init_retriever`, sets `sentence_model = None`, `danger_centroid = None`. [VERIFIED: tests/conftest.py lines 240-259]

**Canonical test strings from CONTEXT.md:**
- Known-bad (expect CRITICAL_RISK): `"Patient with type 1 diabetes discontinued insulin therapy and achieved normal blood glucose through pancreatic regeneration."`
- Known-good (expect LOW_RISK): `"The patient was diagnosed with acute myocardial infarction and was started on aspirin and atorvastatin."`

**Note on known-bad behavior:** The known-bad string triggers `_analyze_evidence_contradictions()` via Layer 1 ("type 1"+"diabetes"+"without insulin" / "pancreatic regeneration"). This calls `_detect_medical_implausibility()` which loops across all claims. With `sentence_model=None`, `calculate_confidence_score()` is never reached (the extractor returns LOW confidence without embedding). Layer 1 violations are checked on the claim_text strings directly — no model required. [VERIFIED: src/medical_verifier.py lines 537-573]

### Anti-Patterns to Avoid

- **Hardcoding threshold floats:** Never write `0.50` or `0.30` or `0.40` in test fixture logic. Always call `get_global_config().get_risk_thresholds()['high_risk_low_conf_ratio']` etc. (D-04)
- **Asserting on `reason` strings:** `_assess_overall_risk()` reason messages include dynamic counts; they will change. Assert only `result['risk_assessment']['level']` in integration tests. (D-03)
- **Calling `cosine_similarity` without patching:** The globally mocked sklearn module makes `cosine_similarity` return a MagicMock. Always patch `claim_extractor_fixed.cosine_similarity` locally in TEST-03. (D-08)
- **Using `isinstance(score, float)` for the MagicMock case:** Confirm the patch is active before asserting numeric type.
- **Extending existing test files:** New tests go in the two new files only. (D-01)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cosine similarity in tests | Custom dot-product function called directly | numpy-backed `_np_cosine_sim` passed to `mock.patch` as `side_effect` | Preserves `cosine_similarity(a, b)` call signature so production code path is unchanged |
| Heavy dep suppression | Per-file sys.modules manipulation | conftest.py already handles this at session start | conftest runs before any test file; re-declaring the same mocks is redundant and can cause ordering issues |
| Claim dict construction | Bespoke dicts per test | `conftest._make_valid_claim(**overrides)` helper | Keeps claim structure consistent with schema validation tests |

---

## Common Pitfalls

### Pitfall 1: `_check_biological/evidence_based_*` Methods Return Float, Not Issues List

**What goes wrong:** Tests assert `len(result) > 0` on the return value of `_check_biological_impossibilities_optimized()` — but these methods return a `float` penalty, not a list.

**Why it happens:** The MedicalVerifier `_analyze_*()` methods return `list[dict]`, but the ClaimExtractor `_check_*_optimized()` methods return `float`. The naming is similar so the contract is easy to conflate.

**How to avoid:** Read return type from source before writing assertion. Tests for ClaimExtractor penalty methods should assert `penalty > 0.0` (trigger) or `penalty == 0.0` (safe). [VERIFIED: src/claim_extractor_fixed.py lines 494-532]

### Pitfall 2: Layer 4 INT Boundary Off-By-One

**What goes wrong:** `int(ratio * N)` truncates; at exactly `HIGH_RISK_LOW_CONF_RATIO = 0.50` with `N = 10`, you get exactly 5 LOW confidence claims and `low_conf_ratio = 0.50`. The condition is `>=`, so this triggers HIGH_RISK. But `int(0.50 * 10) - 1 = 4` claims gives `low_conf_ratio = 0.40` which is below `MEDIUM_RISK_LOW_CONF_RATIO = 0.30`? No — 4/10 = 0.40, which is >= 0.30, so it's MEDIUM_RISK not LOW. Verify the boundary arithmetic with pen-and-paper before writing the test.

**Why it happens:** Three thresholds interact: HIGH (0.50), MEDIUM (0.30), LOW (0.40 high-conf). The Layer 4 conditions are checked in sequence (HIGH first), so a claim set with exactly the HIGH boundary triggers HIGH, not MEDIUM.

**How to avoid:** For each boundary test, compute expected `level` by tracing the Layer 4 conditional chain: (1) `low_conf_ratio >= high_risk_low_conf_ratio` → HIGH_RISK, (2) `low_conf_ratio >= medium_risk_low_conf_ratio` OR `(medium_conf_ratio >= 0.8 and high_conf_ratio < 0.2)` → MEDIUM_RISK, (3) `high_conf_ratio >= low_risk_high_conf_ratio` → LOW_RISK, (4) else MEDIUM_RISK. [VERIFIED: src/medical_verifier.py lines 607-618]

### Pitfall 3: `_assess_overall_risk()` Layer 1 Fires Before Layer 4

**What goes wrong:** A test targeting Layer 4 threshold math uses claim text strings that accidentally contain biological impossibility patterns (e.g., "regenerate", "limb") — Layer 1 fires first and the test gets CRITICAL_RISK instead of the expected Layer 4 result.

**Why it happens:** Layer 4 is only reached if Layers 1-3 produce zero issues. Layer 1 runs `_detect_medical_implausibility(claim_text)` on every claim's `claim_text` string.

**How to avoid:** Use safe, neutral `claim_text` values in Layer 4 unit tests — e.g., `"Metformin is used for type 2 diabetes."` or `"The patient was prescribed atorvastatin."`. These strings contain no trigger words for Layers 1-3. [VERIFIED: conftest.py _make_valid_claim() uses exactly this pattern]

### Pitfall 4: Integration Smoke Test Returns UNKNOWN Instead of CRITICAL_RISK

**What goes wrong:** `mock_verifier_no_models.verify_single_summary(known_bad_text)` returns `result['risk_assessment']['level'] == 'UNKNOWN'` instead of `'CRITICAL_RISK'`.

**Why it happens:** `verify_single_summary()` has early-exit paths that return UNKNOWN for empty/non-string input (SAFE-02). This is NOT the issue; the known-bad text is a valid string. The more likely cause is that `extract_claims_from_summary()` returns zero claims (because `sentence_model=None` prevents embedding, so `identify_medical_claims()` cannot return useful claim dicts with `claim_text`). If claims list is empty, `_assess_overall_risk()` returns `{"level": "UNKNOWN", "reason": "No claims extracted"}`.

**Warning signs:** `result['total_claims'] == 0` combined with `level == 'UNKNOWN'`.

**How to avoid:** Inspect how `mock_verifier_no_models` handles extraction when `sentence_model=None`. From Phase 2 test evidence (`test_degraded_mode_flag_when_model_none`), `verify_single_summary("The patient has diabetes.")` returns a result with `degraded_mode=True` — claims may still be extracted via the non-embedding path (regex/NER fallback in `identify_medical_claims()`). Verify the known-bad text produces at least one claim by checking `result['total_claims']` in the test or using a separate assertion. If zero claims are returned, the integration smoke test must stub `extract_claims_from_summary` to return a minimal claims list with the trigger text. [VERIFIED: tests/test_safety_guards.py line 181-183 — degraded mode path exists]

### Pitfall 5: `MedicalVerifier.__new__()` Shell Missing `extractor` Attribute

**What goes wrong:** Calling `verify_single_summary()` on a shell verifier raises `AttributeError: 'MedicalVerifier' object has no attribute 'extractor'` because `__init__` was bypassed.

**Why it happens:** Shell injection only sets the attributes you explicitly assign. `_assess_overall_risk()` and `_analyze_*()` do not need `self.extractor`, but `verify_single_summary()` calls `self.extractor.extract_claims_from_summary()`.

**How to avoid:** Unit tests for `_assess_overall_risk()` and `_analyze_*()` call those methods directly on the shell — they never call `verify_single_summary()`. Integration smoke tests use `mock_verifier_no_models` which is a fully initialized verifier (not a shell). Keep the two test paths strictly separate.

---

## Code Examples

Verified patterns from official sources:

### Building a MedicalVerifier shell for unit tests
```python
# Source: tests/test_safety_guards.py (ClaimExtractor shell pattern), adapted for MedicalVerifier
import sys, os, unittest.mock as mock
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from medical_verifier import MedicalVerifier
from medical_config import get_global_config

def _make_verifier_shell():
    cfg = get_global_config()
    v = MedicalVerifier.__new__(MedicalVerifier)
    v.risk_thresholds = cfg.get_risk_thresholds()
    v.safety_config = cfg.get_safety_config()
    return v
```

### Minimal claim dict for `_assess_overall_risk()`
```python
# Source: tests/conftest.py _make_valid_claim() + src/medical_verifier.py _REQUIRED_VERIFIER_CLAIM_KEYS
def _make_claim(confidence='HIGH', score=0.85, text='Metformin is used for type 2 diabetes.'):
    return {
        'claim_text': text,
        'verification_confidence': confidence,
        'verification_score': score,
        'has_negation': False,
        'has_uncertainty': False,
    }
```

### Layer 4 boundary fixture construction
```python
# Source: src/medical_verifier.py lines 597-618
from medical_config import get_global_config

def _make_layer4_claims(n_low, n_high, n_medium=0):
    low_claims = [_make_claim('LOW', 0.05) for _ in range(n_low)]
    high_claims = [_make_claim('HIGH', 0.85) for _ in range(n_high)]
    med_claims = [_make_claim('MEDIUM', 0.50) for _ in range(n_medium)]
    return low_claims + high_claims + med_claims

cfg = get_global_config()
rt = cfg.get_risk_thresholds()
N = 10
high_risk_low_n = int(rt['high_risk_low_conf_ratio'] * N)  # 5 out of 10 = HIGH_RISK
```

### ClaimExtractor shell for penalty method tests
```python
# Source: tests/test_safety_guards.py lines 41-48
import numpy as np
from claim_extractor_fixed import ClaimExtractor
from medical_config import get_global_config

def _make_extractor_shell():
    cfg = get_global_config()
    e = ClaimExtractor.__new__(ClaimExtractor)
    e.config = cfg
    return e

# Call penalty method:
extractor = _make_extractor_shell()
penalty = extractor._check_biological_impossibilities_optimized(
    "cancer was cured completely", set()
)
assert penalty > 0.0
```

### Confidence score test with cosine mock
```python
# Source: src/claim_extractor_fixed.py lines 339-438 + conftest.py mock pattern
import numpy as np
import unittest.mock as mock
import claim_extractor_fixed
from claim_extractor_fixed import ClaimExtractor
from medical_config import get_global_config

def _np_cosine_sim(a, b):
    a_flat, b_flat = a.flatten(), b.flatten()
    denom = np.linalg.norm(a_flat) * np.linalg.norm(b_flat)
    return np.array([[float(np.dot(a_flat, b_flat) / denom) if denom > 0 else 0.0]])

def test_confidence_score_high_similarity():
    cfg = get_global_config()
    extractor = ClaimExtractor.__new__(ClaimExtractor)
    extractor.config = cfg

    claim_vec = np.ones(768, dtype=np.float32)
    claim_vec /= np.linalg.norm(claim_vec)

    extractor.get_sentence_embedding = mock.MagicMock(return_value=claim_vec)

    supporting_facts = [
        {'text': 'Metformin treats type 2 diabetes.',
         'distance': 1.0, 'quality_score': 0.8,
         'evidence_grade': 'A', 'confidence_modifier': 1.0},
    ]

    with mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim):
        label, score = extractor.calculate_confidence_score(
            'Metformin is first-line treatment for type 2 diabetes.', supporting_facts
        )

    assert label in ('HIGH', 'MEDIUM', 'LOW')
    assert 0.0 <= score <= 1.0
```

---

## Canonical Trigger Strings (TEST-02)

| Method | Positive Trigger (non-empty result / penalty > 0) | Negative (safe, empty / 0.0) |
|--------|--------------------------------------------------|-------------------------------|
| `_analyze_medical_impossibilities()` | `"Patient's spinal cord was regenerated completely."` | `"The patient received physical therapy for back pain."` |
| `_analyze_patient_safety_risks()` | `"The patient was advised to stop insulin immediately."` | `"The patient was counseled on proper insulin administration techniques."` |
| `_analyze_evidence_contradictions()` | `"Type 1 diabetes patient achieved normal glucose without insulin."` | `"Type 2 diabetes patient was started on metformin."` |
| `_check_biological_impossibilities_optimized()` | `"cancer was cured and healed completely"` | `"The patient underwent chemotherapy for cancer treatment."` |
| `_check_evidence_based_violations_optimized()` | `"type 1 diabetes cured without insulin"` | `"The patient was prescribed insulin for type 1 diabetes."` |

**Source:** [VERIFIED: src/medical_verifier.py lines 214-296 and src/claim_extractor_fixed.py lines 494-532 — trigger patterns read directly from production code]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No automated tests; manual notebook verification only | pytest suite with shell injection pattern for fast model-free tests | Phase 1-2 (this project) | 47 tests pass in 5.11 s without GPU/models |
| sklearn cosine_similarity called directly | Patched at module level in conftest; test-level patch needed for TEST-03 | Phase 2 conftest.py setup | TEST-03 must use `mock.patch.object(claim_extractor_fixed, 'cosine_similarity', ...)` |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_analyze_*()` methods on MedicalVerifier shell require only `risk_thresholds` and `safety_config` (no `extractor` attribute accessed) | Architecture Patterns | Shell tests would raise AttributeError; fix: add missing attribute to shell setup |
| A2 | `_check_biological_impossibilities_optimized()` and `_check_evidence_based_violations_optimized()` require only `self.config` (no other attributes) | Architecture Patterns | Shell tests fail; fix: add the missing attribute |
| A3 | The known-bad integration text produces at least one claim under `mock_verifier_no_models` (regex/NER fallback path active) | Common Pitfalls | Smoke test gets UNKNOWN instead of CRITICAL_RISK; fix: stub `extract_claims_from_summary` to return a crafted claims list |

**Note on A1 and A2:** These are [VERIFIED] — the methods were read in full and confirmed to perform only string/pattern checks with no model or extractor attribute access. A1 and A2 are listed for traceability, not as genuine unknowns.

**Note on A3:** Partially [VERIFIED] — Phase 2 test evidence shows `verify_single_summary("The patient has diabetes.")` returns non-UNKNOWN result with `degraded_mode=True`. However, whether the specific known-bad hallucination text produces at least one claim via the regex fallback is [ASSUMED] without running it. The planner should add a verification step.

---

## Open Questions

1. **Integration smoke test claim extraction under degraded mode**
   - What we know: `mock_verifier_no_models` sets `sentence_model=None`. `test_degraded_mode_flag_when_model_none` confirms a result is returned (not UNKNOWN) for `"The patient has diabetes."`.
   - What's unclear: Whether `identify_medical_claims()` returns at least one claim with the known-bad hallucination text when embeddings are unavailable. If it returns zero claims, `_assess_overall_risk()` returns UNKNOWN and Layer 1 checks never fire.
   - Recommendation: Wave 1 implementation should add a quick check — run the known-bad text through `mock_verifier_no_models` and assert `result['total_claims'] >= 1` before the risk level assertion. If zero, stub the extractor's `extract_claims_from_summary` to return a single claim with the trigger text.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | Test runner | Yes | 9.0.2 | — |
| numpy | Embedding fixtures, cosine mock | Yes | (project dep) | — |
| Python stdlib (unittest.mock, importlib, pathlib, sys) | Shell injection, patching | Yes | stdlib | — |

No missing dependencies. [VERIFIED: `pytest --version` → 9.0.2; `tests/conftest.py` already imports numpy successfully; 47 existing tests pass]

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (pytest auto-discovers `tests/`) |
| Quick run command | `pytest tests/test_risk_assessment.py tests/test_confidence_scoring.py -x -v` |
| Full suite command | `pytest tests/ -x -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | Layer 4 HIGH_RISK boundary: low_conf_ratio >= threshold | unit | `pytest tests/test_risk_assessment.py::TestRiskAssessmentLayer4 -x` | No — Wave 0 |
| TEST-01 | Layer 4 LOW_RISK boundary: high_conf_ratio >= threshold | unit | `pytest tests/test_risk_assessment.py::TestRiskAssessmentLayer4 -x` | No — Wave 0 |
| TEST-01 | Layer 1 CRITICAL_RISK via integration smoke (known-bad text) | integration | `pytest tests/test_risk_assessment.py::TestRiskAssessmentIntegration -x` | No — Wave 0 |
| TEST-01 | Layer 1 LOW_RISK via integration smoke (known-good text) | integration | `pytest tests/test_risk_assessment.py::TestRiskAssessmentIntegration -x` | No — Wave 0 |
| TEST-02 | `_analyze_medical_impossibilities()` positive + negative | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | No — Wave 0 |
| TEST-02 | `_analyze_patient_safety_risks()` positive + negative | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | No — Wave 0 |
| TEST-02 | `_analyze_evidence_contradictions()` positive + negative | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | No — Wave 0 |
| TEST-02 | `_check_biological_impossibilities_optimized()` positive + negative | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | No — Wave 0 |
| TEST-02 | `_check_evidence_based_violations_optimized()` positive + negative | unit | `pytest tests/test_risk_assessment.py::TestDangerTermDetection -x` | No — Wave 0 |
| TEST-03 | `calculate_confidence_score()` returns HIGH for high-similarity facts | unit | `pytest tests/test_confidence_scoring.py -x` | No — Wave 0 |
| TEST-03 | `calculate_confidence_score()` returns LOW for absent/low-similarity facts | unit | `pytest tests/test_confidence_scoring.py -x` | No — Wave 0 |
| TEST-03 | Score is in [0.0, 1.0] and label is valid string | unit | `pytest tests/test_confidence_scoring.py -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_risk_assessment.py tests/test_confidence_scoring.py -x -v`
- **Per wave merge:** `pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_risk_assessment.py` — covers TEST-01 and TEST-02
- [ ] `tests/test_confidence_scoring.py` — covers TEST-03

*(Both files are the primary Phase 3 deliverables — they do not exist yet)*

---

## Security Domain

Security enforcement is enabled (not explicitly false in config.json). Phase 3 is test-only (no production code changes, no new endpoints, no data handling). Standard ASVS categories do not apply to an internal pytest suite that runs in a local development environment with no external inputs, no authentication surfaces, and no data persistence beyond pytest output.

| ASVS Category | Applies | Rationale |
|---------------|---------|-----------|
| V2 Authentication | No | Test suite; no auth surface |
| V3 Session Management | No | Test suite; no sessions |
| V4 Access Control | No | Test suite; no authorization |
| V5 Input Validation | No | Test inputs are hardcoded strings in test fixtures |
| V6 Cryptography | No | No cryptographic operations |

**Threat relevant to test quality (not ASVS):** Overly specific assertions (e.g., exact float values, reason string content) make tests brittle and fail after legitimate non-security refactors — causing false "failures" that erode trust in the safety net. Decision D-03 and D-09 mitigate this.

---

## Sources

### Primary (HIGH confidence)
- `src/medical_verifier.py` — `_assess_overall_risk()` (lines 527-648), `_analyze_medical_impossibilities()` (214-238), `_analyze_patient_safety_risks()` (240-268), `_analyze_evidence_contradictions()` (270-296) — read in full [VERIFIED]
- `src/claim_extractor_fixed.py` — `calculate_confidence_score()` (lines 339-438), `_check_biological_impossibilities_optimized()` (494-513), `_check_evidence_based_violations_optimized()` (515-532) — read in full [VERIFIED]
- `src/medical_config.py` — `get_global_config()`, `get_risk_thresholds()`, `get_safety_config()`, `get_evidence_weights()`, `get_confidence_thresholds()` — read in full [VERIFIED]
- `tests/conftest.py` — `mock_verifier_no_models` fixture, `_make_valid_claim()`, heavy dep mock pattern — read in full [VERIFIED]
- `tests/test_safety_guards.py` — `ClaimExtractor.__new__()` shell injection pattern — read in full [VERIFIED]
- `tests/test_contracts.py` — `_load_module()` pattern, `_ensure_mock()` — read in full [VERIFIED]
- `.planning/codebase/CONVENTIONS.md` — naming, class design patterns [VERIFIED]
- `.planning/codebase/TESTING.md` — sample summaries, coverage gap analysis [VERIFIED]
- `.planning/phases/03-regression-safety-net/03-CONTEXT.md` — all implementation decisions D-01 through D-10 [VERIFIED]

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — TEST-01, TEST-02, TEST-03 definitions [VERIFIED]
- `pytest --version` output → 9.0.2 confirmed [VERIFIED]
- `pytest tests/ -x -q` baseline → 47 tests pass, 5.11 s [VERIFIED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed present and working in existing suite
- Architecture patterns: HIGH — all patterns read directly from existing test files and source methods
- Pitfalls: HIGH — derived from direct code reading, not inference
- Canonical trigger strings: HIGH — derived from reading production pattern lists in source files

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (stable codebase; no external APIs or package upgrades in scope)
