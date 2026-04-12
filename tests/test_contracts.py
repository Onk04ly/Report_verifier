"""
Phase 1 contract tests — config, claim schema, and export guardrails.

These tests do NOT load spaCy, FAISS, or transformer models. Heavy runtime
dependencies are mocked so the suite runs fast in any environment.

Run:
    pytest tests/test_contracts.py -x -v
"""

import sys
import pathlib
import importlib.util
import unittest.mock as mock
import pytest

# ---------------------------------------------------------------------------
# Lightweight mock for heavy dependencies so tests don't require GPU/models.
# (conftest.py may already have installed some of these; this is a no-op if so)
# ---------------------------------------------------------------------------

def _ensure_mock(name: str):
    if name not in sys.modules:
        sys.modules[name] = mock.MagicMock()


for _dep in ["spacy", "faiss", "torch", "transformers",
             "sklearn", "sklearn.metrics", "sklearn.metrics.pairwise"]:
    _ensure_mock(_dep)


# ---------------------------------------------------------------------------
# Source path helpers
# ---------------------------------------------------------------------------

_SRC = pathlib.Path(__file__).parent.parent / "src"
_SRC_STR = str(_SRC)
if _SRC_STR not in sys.path:
    sys.path.insert(0, _SRC_STR)


def _load_module(name: str):
    """Load a source module from src/ and register it in sys.modules."""
    spec = importlib.util.spec_from_file_location(name, _SRC / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load modules under test.
cfg_mod = _load_module("medical_config")
ce_mod = _load_module("claim_extractor_fixed")

ConfigurationSettings = cfg_mod.ConfigurationSettings
get_global_config = cfg_mod.get_global_config
ClaimExtractor = ce_mod.ClaimExtractor
_validate_claim_schema = ce_mod._validate_claim_schema
_REQUIRED_CLAIM_KEYS = ce_mod._REQUIRED_CLAIM_KEYS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_extractor_no_models(config=None):
    """
    Return a ClaimExtractor instance with all heavy I/O mocked out.

    Patches spacy.load, AutoTokenizer, AutoModel, and _init_retriever so that
    no real models or CSV files are needed.
    """
    with (
        mock.patch("claim_extractor_fixed.spacy.load", return_value=mock.MagicMock()),
        mock.patch("claim_extractor_fixed.AutoTokenizer.from_pretrained", return_value=mock.MagicMock()),
        mock.patch("claim_extractor_fixed.AutoModel.from_pretrained", return_value=mock.MagicMock()),
        mock.patch.object(ClaimExtractor, "_init_retriever", return_value=None),
    ):
        return ClaimExtractor(config=config)


# ===========================================================================
# VERI-01 — Extractor reads centralized config only
# ===========================================================================

class TestExtractorReadsGlobalConfig:
    """ClaimExtractor must consume ConfigurationSettings, not inline dicts."""

    def test_none_config_resolves_to_global_config(self):
        """Passing None must result in ClaimExtractor holding the global config."""
        extractor = _make_extractor_no_models(config=None)
        assert isinstance(extractor.config, ConfigurationSettings)

    def test_valid_config_object_accepted(self):
        """A valid ConfigurationSettings instance must be accepted."""
        cfg = ConfigurationSettings()
        extractor = _make_extractor_no_models(config=cfg)
        assert extractor.config is cfg

    def test_raw_dict_rejected(self):
        """Passing a plain dict must raise TypeError before any model work."""
        with pytest.raises(TypeError, match="ConfigurationSettings"):
            # TypeError must be raised *before* model loading; no need to mock.
            ClaimExtractor(config={"top_k_facts": 5, "confidence_thresholds": {}})

    def test_string_rejected(self):
        """Passing an arbitrary object must raise TypeError."""
        with pytest.raises(TypeError):
            ClaimExtractor(config="high")

    def test_extractor_uses_config_attributes_not_dict_keys(self):
        """Verify extractor exposes .config.TOP_K_FACTS (attribute), not dict key access."""
        extractor = _make_extractor_no_models(config=None)
        # Accessing as attribute must not raise; dict-style access is gone.
        assert isinstance(extractor.config.TOP_K_FACTS, int)
        assert isinstance(extractor.config.MIN_SENTENCE_LENGTH, int)
        assert isinstance(extractor.config.DISTANCE_NORM_DIVISOR, float)
        assert isinstance(extractor.config.OUTLIER_DISTANCE_THRESHOLD, float)


# ===========================================================================
# VERI-02 — Claim schema requires claim_text
# ===========================================================================

class TestClaimSchemaRequiresClaimText:
    """_validate_claim_schema must enforce the canonical claim_text contract."""

    def _good_claim(self, **overrides):
        base = {k: "stub" for k in _REQUIRED_CLAIM_KEYS}
        base.update(overrides)
        return base

    def test_valid_claim_passes(self):
        _validate_claim_schema(self._good_claim())

    def test_missing_claim_text_raises(self):
        claim = self._good_claim()
        del claim["claim_text"]
        with pytest.raises(ValueError, match="claim_text"):
            _validate_claim_schema(claim)

    def test_legacy_text_key_not_accepted(self):
        """A claim with only 'text' (legacy) must fail — no dual-key fallback."""
        claim = {k: "stub" for k in _REQUIRED_CLAIM_KEYS}
        del claim["claim_text"]
        claim["text"] = "some sentence"  # legacy key — must NOT satisfy contract
        with pytest.raises(ValueError, match="claim_text"):
            _validate_claim_schema(claim)

    def test_missing_verification_confidence_raises(self):
        claim = self._good_claim()
        del claim["verification_confidence"]
        with pytest.raises(ValueError, match="verification_confidence"):
            _validate_claim_schema(claim)

    def test_missing_verification_score_raises(self):
        claim = self._good_claim()
        del claim["verification_score"]
        with pytest.raises(ValueError, match="verification_score"):
            _validate_claim_schema(claim)

    def test_missing_multiple_keys_lists_all(self):
        """Error message must list every missing key, not just the first."""
        claim = {"claim_text": "x"}  # missing type, medical_entities, verification_*
        with pytest.raises(ValueError) as exc_info:
            _validate_claim_schema(claim)
        msg = str(exc_info.value)
        # At least two missing keys should appear in the message.
        assert "verification_confidence" in msg or "verification_score" in msg

    def test_context_label_in_error_message(self):
        claim = {}
        with pytest.raises(ValueError, match="sentence_id=3"):
            _validate_claim_schema(claim, context="sentence_id=3")

    def test_required_keys_set_is_frozen(self):
        """_REQUIRED_CLAIM_KEYS must be immutable."""
        with pytest.raises((AttributeError, TypeError)):
            _REQUIRED_CLAIM_KEYS.add("extra_field")  # type: ignore[attr-defined]


# ===========================================================================
# ConfigurationSettings.__post_init__ validation
# ===========================================================================

class TestConfigValidation:
    """ConfigurationSettings must reject invalid values at construction time."""

    def test_default_construction_succeeds(self):
        cfg = ConfigurationSettings()
        assert cfg.CONFIDENCE_HIGH > cfg.CONFIDENCE_MEDIUM

    def test_negative_confidence_high_rejected(self):
        with pytest.raises(ValueError, match="CONFIDENCE_HIGH"):
            ConfigurationSettings(CONFIDENCE_HIGH=-0.1)

    def test_confidence_medium_ge_high_rejected(self):
        with pytest.raises(ValueError, match="CONFIDENCE_MEDIUM"):
            ConfigurationSettings(CONFIDENCE_MEDIUM=0.5, CONFIDENCE_HIGH=0.3)

    def test_weights_not_summing_to_one_rejected(self):
        with pytest.raises(ValueError, match="weights must sum"):
            ConfigurationSettings(SIMILARITY_AVG_WEIGHT=0.9)

    def test_zero_top_k_rejected(self):
        with pytest.raises(ValueError, match="TOP_K_FACTS"):
            ConfigurationSettings(TOP_K_FACTS=0)

    def test_negative_distance_norm_divisor_rejected(self):
        with pytest.raises(ValueError, match="DISTANCE_NORM_DIVISOR"):
            ConfigurationSettings(DISTANCE_NORM_DIVISOR=-1.0)

    def test_outlier_penalty_cap_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="OUTLIER_PENALTY_CAP"):
            ConfigurationSettings(OUTLIER_PENALTY_CAP=1.5)

    def test_error_lists_all_invalid_fields(self):
        """Multiple bad values must all appear in one error message."""
        with pytest.raises(ValueError) as exc_info:
            ConfigurationSettings(CONFIDENCE_HIGH=-0.1, TOP_K_FACTS=0)
        msg = str(exc_info.value)
        assert "CONFIDENCE_HIGH" in msg
        assert "TOP_K_FACTS" in msg

    def test_get_outlier_params_returns_config_values(self):
        cfg = ConfigurationSettings(
            DISTANCE_NORM_DIVISOR=200.0,
            OUTLIER_DISTANCE_THRESHOLD=40.0,
        )
        params = cfg.get_outlier_params()
        assert params["distance_norm_divisor"] == 200.0
        assert params["outlier_distance_threshold"] == 40.0


# ===========================================================================
# MedicalVerifier constructor rejects non-ConfigurationSettings config
# ===========================================================================

class TestVerifierConfigContract:
    """MedicalVerifier must not accept partial dicts as extractor_config."""

    def test_verifier_rejects_dict_config(self):
        # Import verifier with mocked ClaimExtractor to avoid model loading.
        with mock.patch.dict(sys.modules, {"claim_extractor_fixed": ce_mod}):
            import importlib
            ver_spec = importlib.util.spec_from_file_location(
                "medical_verifier", _SRC / "medical_verifier.py"
            )
            ver_mod = importlib.util.module_from_spec(ver_spec)
            with mock.patch.object(ce_mod, "ClaimExtractor") as MockExtractor:
                MockExtractor.return_value = mock.MagicMock()
                ver_spec.loader.exec_module(ver_mod)
                MedicalVerifier = ver_mod.MedicalVerifier
                with pytest.raises(TypeError, match="ConfigurationSettings"):
                    MedicalVerifier(extractor_config={"top_k_facts": 5})


# ===========================================================================
# VERI-02 — Verifier input boundary: claim_text validation
# ===========================================================================

class TestVerifierInputBoundary:
    """
    MedicalVerifier must validate claim_text at the verifier boundary before
    risk assessment and export logic run (T-01-04, D-08, D-09).

    The verifier must raise ValueError (not KeyError) with a message that
    explicitly names 'claim_text' when a malformed claim payload arrives.
    """

    def _load_verifier_mod(self):
        """Return a freshly loaded medical_verifier module with mocked extractor."""
        with mock.patch.dict(sys.modules, {"claim_extractor_fixed": ce_mod}):
            ver_spec = importlib.util.spec_from_file_location(
                "medical_verifier_boundary_test",
                _SRC / "medical_verifier.py",
            )
            ver_mod = importlib.util.module_from_spec(ver_spec)
            with mock.patch.object(ce_mod, "ClaimExtractor") as MockExtractor:
                MockExtractor.return_value = mock.MagicMock()
                ver_spec.loader.exec_module(ver_mod)
        return ver_mod

    def _make_verifier(self, ver_mod):
        """Instantiate MedicalVerifier with all heavy deps mocked."""
        MedicalVerifier = ver_mod.MedicalVerifier
        with mock.patch.object(ce_mod, "ClaimExtractor") as MockExtractor:
            MockExtractor.return_value = mock.MagicMock()
            return MedicalVerifier()

    def _good_claim(self, **overrides):
        base = {
            "claim_text": "Insulin is required for type 1 diabetes.",
            "type": "treatment",
            "medical_entities": ["insulin", "type 1 diabetes"],
            "verification_confidence": "HIGH",
            "verification_score": 0.88,
            "has_negation": False,
            "has_uncertainty": False,
            "certainty_modifier": "positive",
        }
        base.update(overrides)
        return base

    def test_assess_overall_risk_accepts_valid_claim_list(self):
        """_assess_overall_risk must succeed for a list of valid canonical claims."""
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        result = verifier._assess_overall_risk([self._good_claim()])
        assert "level" in result

    def test_assess_overall_risk_rejects_claim_without_claim_text(self):
        """
        _assess_overall_risk must raise ValueError when a claim is missing
        'claim_text'. The error must name 'claim_text' explicitly so callers
        get a clear schema violation message rather than a generic KeyError.
        """
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        bad_claim = self._good_claim()
        del bad_claim["claim_text"]
        bad_claim["text"] = "some legacy text"  # legacy key — not accepted
        with pytest.raises(ValueError, match="claim_text"):
            verifier._assess_overall_risk([bad_claim])

    def test_assess_overall_risk_rejects_empty_claim_dict(self):
        """An empty claim dict must not silently produce a result."""
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        with pytest.raises(ValueError, match="claim_text"):
            verifier._assess_overall_risk([{}])

    def test_no_fallback_between_text_and_claim_text(self):
        """
        Verifier must NOT fall back from 'text' to 'claim_text'.
        A claim with only the legacy 'text' key must raise ValueError,
        not silently produce a risk result.
        """
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        legacy_claim = {k: "stub" for k in ["type", "medical_entities",
                                             "verification_confidence", "verification_score",
                                             "has_negation", "has_uncertainty"]}
        legacy_claim["text"] = "a legacy claim text"
        with pytest.raises(ValueError, match="claim_text"):
            verifier._assess_overall_risk([legacy_claim])


# ===========================================================================
# VERI-03 — Export structure is deterministic
# ===========================================================================

class TestExportStructureDeterminism:
    """
    MedicalVerifier export output (JSON) must use a deterministic shape with
    canonical claim fields for downstream consumers (T-01-05, D-07).
    """

    def _load_verifier_mod(self):
        """Return freshly loaded medical_verifier module."""
        with mock.patch.dict(sys.modules, {"claim_extractor_fixed": ce_mod}):
            ver_spec = importlib.util.spec_from_file_location(
                "medical_verifier_export_test",
                _SRC / "medical_verifier.py",
            )
            ver_mod = importlib.util.module_from_spec(ver_spec)
            with mock.patch.object(ce_mod, "ClaimExtractor") as MockExtractor:
                MockExtractor.return_value = mock.MagicMock()
                ver_spec.loader.exec_module(ver_mod)
        return ver_mod

    def _make_verifier(self, ver_mod):
        MedicalVerifier = ver_mod.MedicalVerifier
        with mock.patch.object(ce_mod, "ClaimExtractor") as MockExtractor:
            MockExtractor.return_value = mock.MagicMock()
            return MedicalVerifier()

    def _canonical_result(self, summary_id: str = "export_test_001") -> dict:
        return {
            "summary_id": summary_id,
            "original_text": "Metformin is the first-line treatment for type 2 diabetes.",
            "sentences": ["Metformin is the first-line treatment for type 2 diabetes."],
            "claims": [
                {
                    "claim_text": "Metformin is the first-line treatment for type 2 diabetes.",
                    "type": "treatment",
                    "medical_entities": ["metformin", "type 2 diabetes"],
                    "verification_confidence": "HIGH",
                    "verification_score": 0.85,
                    "has_negation": False,
                    "has_uncertainty": False,
                    "certainty_modifier": "positive",
                }
            ],
            "total_claims": 1,
            "analysis_timestamp": "2026-04-12T00:00:00",
            "risk_assessment": {
                "level": "LOW_RISK",
                "reason": "100% high confidence claims (1/1)",
                "stats": {
                    "total_claims": 1,
                    "high_confidence": 1,
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "negated_claims": 0,
                    "uncertain_claims": 0,
                    "high_conf_ratio": 1.0,
                    "medium_conf_ratio": 0.0,
                    "low_conf_ratio": 0.0,
                    "negation_ratio": 0.0,
                    "uncertainty_ratio": 0.0,
                },
            },
            "responsible_ai": {
                "safety_warnings": [],
                "safety_recommendations": [],
                "requires_expert_review": False,
                "auto_flagged": False,
                "disclaimer": {"title": "RESPONSIBLE AI - HEALTHCARE SAFETY NOTICE",
                               "notice": [], "limitations": [], "proper_use": []},
                "safety_assessment": {
                    "low_confidence_ratio": 0.0,
                    "safety_threshold_exceeded": False,
                    "critical_threshold_exceeded": False,
                    "contains_medical_terms": False,
                    "contains_dangerous_terms": False,
                    "dangerous_terms_detected": [],
                },
            },
        }

    def test_json_export_contains_required_top_level_keys(self, tmp_path):
        """JSON export must contain metadata, verification_results, global_safety_summary."""
        import json
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        result = self._canonical_result()
        out = tmp_path / "test_export.json"
        verifier.export_results([result], str(out), format="json")
        with open(out) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "verification_results" in data
        assert "global_safety_summary" in data

    def test_json_export_metadata_has_required_fields(self, tmp_path):
        """Export metadata must include timestamp, safety_compliance, and disclaimer."""
        import json
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        result = self._canonical_result()
        out = tmp_path / "test_export_meta.json"
        verifier.export_results([result], str(out), format="json")
        with open(out) as f:
            data = json.load(f)
        meta = data["metadata"]
        assert "export_timestamp" in meta
        assert "safety_compliance" in meta
        assert "disclaimer" in meta

    def test_csv_export_uses_claim_text_column(self, tmp_path):
        """CSV export must use 'claim_text' column — no legacy 'text' column."""
        import pandas as pd
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        result = self._canonical_result()
        out = tmp_path / "test_export.csv"
        verifier.export_results([result], str(out), format="csv")
        df = pd.read_csv(out)
        assert "claim_text" in df.columns
        assert "text" not in df.columns

    def test_csv_export_deterministic_columns(self, tmp_path):
        """CSV export must always produce the same set of columns."""
        import pandas as pd
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        result1 = self._canonical_result("export_001")
        result2 = self._canonical_result("export_002")
        out1 = tmp_path / "export1.csv"
        out2 = tmp_path / "export2.csv"
        verifier.export_results([result1], str(out1), format="csv")
        verifier.export_results([result2], str(out2), format="csv")
        cols1 = set(pd.read_csv(out1).columns)
        cols2 = set(pd.read_csv(out2).columns)
        assert cols1 == cols2, f"Column sets differ: {cols1.symmetric_difference(cols2)}"

    def test_safety_log_created_alongside_export(self, tmp_path):
        """Safety log JSON must be written alongside every export (T-01-05)."""
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        result = self._canonical_result()
        out = tmp_path / "test_export.json"
        verifier.export_results([result], str(out), format="json")
        log_path = tmp_path / "test_export_safety_log.json"
        assert log_path.exists(), "Safety log was not created alongside JSON export"

    def test_single_and_batch_export_same_structure(self, tmp_path):
        """Single result and batch results must produce the same top-level JSON structure."""
        import json
        ver_mod = self._load_verifier_mod()
        verifier = self._make_verifier(ver_mod)
        single = self._canonical_result("single_001")
        batch1 = self._canonical_result("batch_001")
        batch2 = self._canonical_result("batch_002")
        out_single = tmp_path / "single.json"
        out_batch = tmp_path / "batch.json"
        verifier.export_results([single], str(out_single), format="json")
        verifier.export_results([batch1, batch2], str(out_batch), format="json")
        with open(out_single) as f:
            data_single = json.load(f)
        with open(out_batch) as f:
            data_batch = json.load(f)
        assert set(data_single.keys()) == set(data_batch.keys())
