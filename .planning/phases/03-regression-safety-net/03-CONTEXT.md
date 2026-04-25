# Phase 3: Regression Safety Net - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Add automated tests that prevent silent quality regressions in the three safety-critical logic areas: (TEST-01) four-layer risk assessment boundaries, (TEST-02) dangerous-term and evidence-violation detection, (TEST-03) confidence score computation. No production code changes — test files only.

</domain>

<decisions>
## Implementation Decisions

### Test File Organization
- **D-01:** Create two new test files: `tests/test_risk_assessment.py` (TEST-01 + TEST-02) and `tests/test_confidence_scoring.py` (TEST-03). Do not extend existing test files.

### Risk Boundary Tests (TEST-01)
- **D-02:** Use both direct unit tests AND integration smoke tests for `_assess_overall_risk()`.
  - **Unit path:** `MedicalVerifier.__new__()` shell + inject `risk_thresholds` and `safety_config` from `get_global_config()`. Feed minimal claim dicts directly. Covers Layer 4 threshold math precisely.
  - **Integration path:** Use `mock_verifier_no_models` fixture (already in conftest.py) + feed crafted text strings via `verify_single_summary()`. Covers Layer 1 implausibility triggers.
- **D-03:** Integration smoke tests assert `result['risk_assessment']['level']` only — not the `reason` string or sub-fields. Stable against reason formatting changes.
- **D-04:** Layer 4 threshold boundary tests derive claim counts dynamically from `get_global_config()` (e.g., `int(threshold * N)` to hit exact boundary). Never hardcode threshold values (0.60, 0.40, 0.70) in test fixtures — thresholds must be sourced from config exactly as production code does.

### Dangerous-Term Detection Tests (TEST-02)
- **D-05:** Test each of the 5 detection methods directly via `MedicalVerifier.__new__()` and `ClaimExtractor.__new__()` shell injection. Methods under test:
  - `MedicalVerifier._analyze_medical_impossibilities()`
  - `MedicalVerifier._analyze_patient_safety_risks()`
  - `MedicalVerifier._analyze_evidence_contradictions()`
  - `ClaimExtractor._check_biological_impossibilities_optimized()`
  - `ClaimExtractor._check_evidence_based_violations_optimized()`
- **D-06:** 1-2 canonical trigger strings per method: one positive trigger (expect non-empty issues list) and one negative (safe clinical text, expect empty list). No per-family exhaustive coverage in Phase 3.
- **D-07:** Go into `tests/test_risk_assessment.py` (same file as TEST-01, different TestClass).

### Confidence Score Tests (TEST-03)
- **D-08:** Mock `ClaimExtractor.get_sentence_embedding()` to return fixed deterministic numpy arrays. Do NOT use sklearn `cosine_similarity` — it is mocked as MagicMock in test env (same issue as Phase 2). Implement cosine comparison via numpy dot product in test setup if needed.
- **D-09:** Assert `(label, score)` return: label is `'HIGH'`/`'MEDIUM'`/`'LOW'` and numeric score is in `[0.0, 1.0]`. No exact float assertions.
- **D-10:** Two fixture cases minimum: high-similarity supporting facts (expect `'HIGH'`) and low-similarity/absent facts (expect `'LOW'`).

### Claude's Discretion
- Internal TestClass naming, exact fixture variable names, and which specific canonical trigger strings to use can follow existing conventions from `test_safety_guards.py` and `test_contracts.py`.
- Number of integration smoke test cases (known-good + known-bad summaries) is Claude's call — 2-4 is sufficient.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` — Phase 3 section: "Regression Safety Net", success criteria 1–4
- `.planning/REQUIREMENTS.md` — `TEST-01`, `TEST-02`, `TEST-03` definitions

### Source Modules Under Test
- `src/medical_verifier.py` — `_assess_overall_risk()` (line 527), `_analyze_medical_impossibilities()` (line 214), `_analyze_patient_safety_risks()` (line 240), `_analyze_evidence_contradictions()` (line 270)
- `src/claim_extractor_fixed.py` — `calculate_confidence_score()` (line 339), `_check_biological_impossibilities_optimized()` (line 494), `_check_evidence_based_violations_optimized()` (line 515)
- `src/medical_config.py` — `get_global_config()`, `get_risk_thresholds()`, `get_safety_config()`, `get_evidence_weights()`

### Existing Test Infrastructure (read before writing new tests)
- `tests/conftest.py` — `mock_verifier_no_models` fixture (Phase 2), other shared fixtures
- `tests/test_contracts.py` — established mock pattern for heavy deps (spacy/faiss/transformers)
- `tests/test_safety_guards.py` — `ClaimExtractor.__new__()` shell injection pattern

### Codebase Conventions
- `.planning/codebase/CONVENTIONS.md` — naming patterns, error handling, module structure
- `.planning/codebase/TESTING.md` — existing test data, sample summaries, priority areas

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mock_verifier_no_models` fixture in `conftest.py`: patches `SentenceTransformer` → None, patches `ClaimExtractor._init_retriever` — use directly for integration smoke tests
- `ClaimExtractor.__new__()` shell injection pattern: bypass `__init__`, set `self.config = get_global_config()`, `self.sentence_model = None`, `self.danger_centroid = None` — established in Phase 2 for extractor unit tests
- `MedicalVerifier.__new__()` shell injection: set `self.risk_thresholds = get_global_config().get_risk_thresholds()`, `self.safety_config = get_global_config().get_safety_config()` — sufficient for `_assess_overall_risk()` and `_analyze_*()` methods
- Heavy dep mock pattern (from `test_contracts.py` top of file): mock `spacy`, `faiss`, `torch`, `transformers`, `sklearn.metrics.pairwise` via `sys.modules` before module load

### Established Patterns
- All test files add heavy dep mocks via `sys.modules` before importing source modules
- Tests use `importlib.util.spec_from_file_location` to load modules from `src/` without package install
- Claim dicts for `_assess_overall_risk()` require: `claim_text` (str), `verification_confidence` ('HIGH'/'MEDIUM'/'LOW'), `verification_score` (float)

### Integration Points
- `tests/conftest.py` already imports and patches `claim_extractor_fixed` — new test files can rely on the same conftest fixtures without re-declaring patches
- `test_risk_assessment.py` and `test_confidence_scoring.py` sit alongside existing files in `tests/` with no changes to `conftest.py` required (unless new shared fixtures emerge during planning)

</code_context>

<specifics>
## Specific Ideas

- Use the 16-case sample summaries from `medial_verfication.txt` (4 categories: standard, uncertainty, hallucination, complex) as the canonical source for integration smoke test strings. Known-bad: "Patient with type 1 diabetes discontinued insulin therapy and achieved normal blood glucose through pancreatic regeneration." Known-good: "The patient was diagnosed with acute myocardial infarction and was started on aspirin and atorvastatin."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-regression-safety-net*
*Context gathered: 2026-04-25*
