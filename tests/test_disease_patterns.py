"""
Tests for Phase 5 Plan 02 — disease-specific Layer 1 patterns in MedicalVerifier.

TDD — RED phase: these tests should FAIL before Task 2 implementation.

Tests verify:
  - _get_disease_patterns(disease_slug) method exists on MedicalVerifier
  - type1_diabetes patterns: 3 patterns covering beta-cell regen, insulin independence, fixed dose
  - metastatic_cancer patterns: 3 patterns covering stage4 cure, chemo avoidance, metastasis reversal
  - Unknown disease slug returns [] without raising
  - _detect_medical_implausibility() accepts optional disease=None parameter
  - When disease is active, disease_issues are appended to all_issues
  - Slug validation uses self.global_config.DISEASE_LIST (not hardcoded strings in dispatch)
"""

import pytest
import types
import sys
import os


def _load_source():
    """Return raw source text of medical_verifier.py."""
    src_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'medical_verifier.py')
    with open(src_path, encoding='utf-8') as f:
        return f.read()


def _make_stub_verifier():
    """
    Construct a minimal MedicalVerifier stub that has _get_disease_patterns and
    _detect_medical_implausibility wired but skips heavy __init__ (no ML models).
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    import medical_verifier as mv_module
    from medical_config import get_global_config

    verifier = object.__new__(mv_module.MedicalVerifier)
    verifier.global_config = get_global_config()
    verifier.safety_config = verifier.global_config.get_safety_config()
    verifier.risk_thresholds = verifier.global_config.get_risk_thresholds()
    return verifier


class TestGetDiseasePatternsMethodExists:
    """Verify _get_disease_patterns is defined on MedicalVerifier."""

    def test_method_exists_on_class(self):
        sys.path.insert(0, 'src')
        import medical_verifier
        assert hasattr(medical_verifier.MedicalVerifier, '_get_disease_patterns'), (
            "_get_disease_patterns not found on MedicalVerifier class"
        )

    def test_method_accepts_disease_slug(self):
        import inspect
        import medical_verifier
        sig = inspect.signature(medical_verifier.MedicalVerifier._get_disease_patterns)
        params = list(sig.parameters.keys())
        assert 'disease_slug' in params, f"disease_slug not in params: {params}"


class TestSourceStructureTask2:
    """Verify source-level structure without instantiating heavy ML models."""

    @pytest.fixture(autouse=True)
    def load_src(self):
        self.src = _load_source()

    def test_get_disease_patterns_defined(self):
        assert 'def _get_disease_patterns(self, disease_slug: str)' in self.src, (
            "_get_disease_patterns not found in medical_verifier.py source"
        )

    def test_detect_implausibility_has_disease_param(self):
        assert 'def _detect_medical_implausibility(self, claim_text, disease=None)' in self.src, (
            "_detect_medical_implausibility signature does not include disease=None"
        )

    def test_disease_specific_impossibility_present(self):
        import re
        patterns = re.findall(r"'type': '(disease_specific_[^']+)'", self.src)
        assert 'disease_specific_impossibility' in patterns, (
            "No 'disease_specific_impossibility' type found in _get_disease_patterns"
        )

    def test_disease_specific_contradiction_present(self):
        import re
        patterns = re.findall(r"'type': '(disease_specific_[^']+)'", self.src)
        assert 'disease_specific_contradiction' in patterns, (
            "No 'disease_specific_contradiction' type found in _get_disease_patterns"
        )

    def test_disease_list_guard_present(self):
        assert 'disease in self.global_config.DISEASE_LIST' in self.src, (
            "Slug validation via self.global_config.DISEASE_LIST not found; "
            "hardcoded slug strings should not appear in _detect_medical_implausibility dispatch"
        )

    def test_disease_get_patterns_call_present(self):
        assert 'disease_issues = self._get_disease_patterns(disease)' in self.src, (
            "disease_issues = self._get_disease_patterns(disease) not found in source"
        )

    def test_current_claim_lower_attribute_set(self):
        assert 'self._current_claim_lower' in self.src, (
            "self._current_claim_lower attribute not found; required by _get_disease_patterns"
        )

    def test_t1d_branch_present(self):
        assert '"type1_diabetes"' in self.src or "'type1_diabetes'" in self.src, (
            "type1_diabetes branch not found in _get_disease_patterns"
        )

    def test_metastatic_cancer_branch_present(self):
        assert '"metastatic_cancer"' in self.src or "'metastatic_cancer'" in self.src, (
            "metastatic_cancer branch not found in _get_disease_patterns"
        )

    def test_disease_issues_appended_to_all_issues(self):
        assert 'disease_issues' in self.src, (
            "disease_issues variable not found in source"
        )
        # Check it's concatenated into all_issues
        assert '+ disease_issues' in self.src or 'disease_issues' in self.src, (
            "disease_issues not appended to all_issues"
        )

    def test_endocrinology_domain_present(self):
        assert 'endocrinology' in self.src, (
            "'endocrinology' medical_domain missing from T1D patterns"
        )

    def test_oncology_domain_present(self):
        assert 'oncology' in self.src, (
            "'oncology' medical_domain missing from metastatic_cancer patterns"
        )

    def test_critical_severity_in_t1d_patterns(self):
        assert "'severity': 'CRITICAL'" in self.src, (
            "No CRITICAL severity found in disease patterns"
        )

    def test_high_severity_in_patterns(self):
        assert "'severity': 'HIGH'" in self.src, (
            "No HIGH severity found in disease patterns"
        )


class TestGetDiseasePatternsLogicUnit:
    """
    Unit tests for _get_disease_patterns logic using a stub verifier.
    """

    @pytest.fixture
    def verifier(self):
        return _make_stub_verifier()

    # ------------------------------------------------------------------ #
    # type1_diabetes patterns
    # ------------------------------------------------------------------ #

    def test_t1d_beta_cell_regen_pattern_fires(self, verifier):
        """Pattern (a): beta-cell regeneration claim triggers CRITICAL issue."""
        verifier._current_claim_lower = "type 1 diabetes can be cured by regenerating beta cells"
        issues = verifier._get_disease_patterns("type1_diabetes")
        types_ = [i['type'] for i in issues]
        severities = [i['severity'] for i in issues]
        assert 'disease_specific_impossibility' in types_, (
            f"T1D beta-cell regen pattern did not fire. Issues: {issues}"
        )
        assert 'CRITICAL' in severities

    def test_t1d_insulin_independence_pattern_fires(self, verifier):
        """Pattern (b): insulin independence claim triggers CRITICAL issue."""
        verifier._current_claim_lower = "type 1 diabetic patient is now without insulin after 6 months"
        issues = verifier._get_disease_patterns("type1_diabetes")
        types_ = [i['type'] for i in issues]
        assert 'disease_specific_contradiction' in types_, (
            f"T1D insulin-independence pattern did not fire. Issues: {issues}"
        )

    def test_t1d_fixed_dose_pattern_fires(self, verifier):
        """Pattern (c): universal fixed dose claim triggers HIGH issue."""
        verifier._current_claim_lower = "type 1 diabetes patients should use the same dose of insulin"
        issues = verifier._get_disease_patterns("type1_diabetes")
        types_ = [i['type'] for i in issues]
        severities = [i['severity'] for i in issues]
        assert 'disease_specific_impossibility' in types_, (
            f"T1D fixed-dose pattern did not fire. Issues: {issues}"
        )
        assert 'HIGH' in severities

    def test_t1d_normal_claim_no_patterns(self, verifier):
        """Benign T1D claim does not trigger disease-specific patterns."""
        verifier._current_claim_lower = "type 1 diabetes requires daily insulin injections and monitoring"
        issues = verifier._get_disease_patterns("type1_diabetes")
        assert len(issues) == 0, f"Unexpected issues for benign T1D claim: {issues}"

    def test_t1d_type2_diabetes_not_triggered_by_type2(self, verifier):
        """Pattern (a) should NOT fire when 'type 2' is mentioned (type 2 can have beta-cell recovery)."""
        verifier._current_claim_lower = "type 2 diabetes can be reversed restoring some beta cell function"
        issues = verifier._get_disease_patterns("type1_diabetes")
        # Pattern (a) requires 'type 1' and NOT 'type 2' — should not fire for type 2 only
        impossibility_issues = [i for i in issues if i['type'] == 'disease_specific_impossibility'
                                 and 'beta' in i.get('reason', '').lower()]
        assert len(impossibility_issues) == 0, (
            f"T1D beta-cell regen pattern incorrectly fired for type 2 claim: {impossibility_issues}"
        )

    # ------------------------------------------------------------------ #
    # metastatic_cancer patterns
    # ------------------------------------------------------------------ #

    def test_metastatic_cure_pattern_fires(self, verifier):
        """Pattern (a): complete cure claim for metastatic cancer triggers HIGH issue."""
        verifier._current_claim_lower = "metastatic breast cancer was completely cured after treatment"
        issues = verifier._get_disease_patterns("metastatic_cancer")
        types_ = [i['type'] for i in issues]
        assert 'disease_specific_contradiction' in types_, (
            f"Metastatic cure pattern did not fire. Issues: {issues}"
        )

    def test_metastatic_cure_with_remission_not_triggered(self, verifier):
        """Pattern (a) should NOT fire when 'remission' is present (clinically valid)."""
        verifier._current_claim_lower = "metastatic cancer achieved complete remission after immunotherapy"
        issues = verifier._get_disease_patterns("metastatic_cancer")
        # Cure pattern (a) excludes 'remission'
        impossibility_issues = [i for i in issues
                                 if 'cure' in i.get('reason', '').lower()
                                 or 'eradicat' in i.get('reason', '').lower()]
        assert len(impossibility_issues) == 0, (
            f"Cure pattern incorrectly fired when 'remission' present: {impossibility_issues}"
        )

    def test_chemo_avoidance_pattern_fires(self, verifier):
        """Pattern (b): chemo avoidance + resolution claim triggers HIGH issue."""
        verifier._current_claim_lower = "metastatic cancer resolved without chemotherapy using herbal protocol"
        issues = verifier._get_disease_patterns("metastatic_cancer")
        types_ = [i['type'] for i in issues]
        assert 'disease_specific_contradiction' in types_, (
            f"Chemo-avoidance pattern did not fire. Issues: {issues}"
        )

    def test_metastasis_reversal_alternative_fires(self, verifier):
        """Pattern (c): metastasis reversed via diet/herbs triggers CRITICAL issue."""
        verifier._current_claim_lower = "metastasis disappeared after a strict diet and herbal supplements"
        issues = verifier._get_disease_patterns("metastatic_cancer")
        types_ = [i['type'] for i in issues]
        severities = [i['severity'] for i in issues]
        assert 'disease_specific_impossibility' in types_, (
            f"Metastasis-reversal-via-alternatives pattern did not fire. Issues: {issues}"
        )
        assert 'CRITICAL' in severities

    def test_metastatic_normal_claim_no_patterns(self, verifier):
        """Benign metastatic cancer claim does not trigger disease-specific patterns."""
        verifier._current_claim_lower = "metastatic cancer patients receive systemic chemotherapy and targeted therapy"
        issues = verifier._get_disease_patterns("metastatic_cancer")
        assert len(issues) == 0, f"Unexpected issues for benign metastatic claim: {issues}"

    # ------------------------------------------------------------------ #
    # Unknown slug
    # ------------------------------------------------------------------ #

    def test_unknown_slug_returns_empty(self, verifier):
        """Unknown disease slug must return [] without raising."""
        verifier._current_claim_lower = "some claim text"
        issues = verifier._get_disease_patterns("unknown_disease")
        assert issues == [], f"Expected [] for unknown slug, got: {issues}"

    def test_empty_slug_returns_empty(self, verifier):
        """Empty string slug must return [] without raising."""
        verifier._current_claim_lower = "some claim text"
        issues = verifier._get_disease_patterns("")
        assert issues == [], f"Expected [] for empty slug, got: {issues}"

    # ------------------------------------------------------------------ #
    # Issue dict schema
    # ------------------------------------------------------------------ #

    def test_issue_dict_has_required_keys(self, verifier):
        """All returned issue dicts must have type, severity, reason, medical_domain."""
        verifier._current_claim_lower = "type 1 diabetes can be cured by regenerating beta cells"
        issues = verifier._get_disease_patterns("type1_diabetes")
        for issue in issues:
            for key in ('type', 'severity', 'reason', 'medical_domain'):
                assert key in issue, (
                    f"Issue dict missing '{key}' key: {issue}"
                )

    def test_t1d_medical_domain_is_endocrinology(self, verifier):
        """T1D issues should have medical_domain='endocrinology'."""
        verifier._current_claim_lower = "type 1 diabetes can be cured by regenerating beta cells"
        issues = verifier._get_disease_patterns("type1_diabetes")
        for issue in issues:
            assert issue.get('medical_domain') == 'endocrinology', (
                f"Expected endocrinology domain for T1D issue, got: {issue.get('medical_domain')}"
            )

    def test_metastatic_medical_domain_is_oncology(self, verifier):
        """Metastatic cancer issues should have medical_domain='oncology'."""
        verifier._current_claim_lower = "metastatic breast cancer was completely cured after treatment"
        issues = verifier._get_disease_patterns("metastatic_cancer")
        for issue in issues:
            assert issue.get('medical_domain') == 'oncology', (
                f"Expected oncology domain for metastatic issue, got: {issue.get('medical_domain')}"
            )


class TestDetectMedicalImplausibilityWithDisease:
    """
    Tests for _detect_medical_implausibility() with optional disease parameter.
    """

    @pytest.fixture
    def verifier(self):
        return _make_stub_verifier()

    def test_disease_none_does_not_call_get_disease_patterns(self, verifier, monkeypatch):
        """When disease=None, _get_disease_patterns must NOT be called."""
        called = []

        def _mock_get_disease_patterns(slug):
            called.append(slug)
            return []

        verifier._get_disease_patterns = _mock_get_disease_patterns
        verifier._detect_medical_implausibility("some benign claim", disease=None)
        assert called == [], (
            f"_get_disease_patterns was called with disease=None: {called}"
        )

    def test_disease_not_in_list_does_not_call_patterns(self, verifier, monkeypatch):
        """When disease is not in DISEASE_LIST, _get_disease_patterns must NOT be called."""
        called = []

        def _mock_get_disease_patterns(slug):
            called.append(slug)
            return []

        verifier._get_disease_patterns = _mock_get_disease_patterns
        verifier._detect_medical_implausibility("some claim", disease="unknown_disease_xyz")
        assert called == [], (
            f"_get_disease_patterns was called for unlisted disease: {called}"
        )

    def test_valid_disease_appends_patterns_to_all_issues(self, verifier, monkeypatch):
        """When disease is a valid slug, disease_issues are appended to all_issues."""
        fake_disease_issue = {
            'type': 'disease_specific_impossibility',
            'severity': 'CRITICAL',
            'reason': 'Test reason',
            'medical_domain': 'endocrinology',
        }

        def _mock_get_disease_patterns(slug):
            if slug == 'type1_diabetes':
                return [fake_disease_issue]
            return []

        verifier._get_disease_patterns = _mock_get_disease_patterns
        issues = verifier._detect_medical_implausibility(
            "some claim about diabetes", disease="type1_diabetes"
        )
        assert fake_disease_issue in issues, (
            f"Disease-specific issue not found in all_issues. Got: {issues}"
        )

    def test_implausibility_disease_param_default_is_none(self):
        """_detect_medical_implausibility signature must have disease=None default."""
        import inspect
        import medical_verifier
        sig = inspect.signature(medical_verifier.MedicalVerifier._detect_medical_implausibility)
        params = sig.parameters
        assert 'disease' in params, f"'disease' param missing from _detect_medical_implausibility"
        assert params['disease'].default is None, (
            f"'disease' param default must be None, got: {params['disease'].default!r}"
        )
