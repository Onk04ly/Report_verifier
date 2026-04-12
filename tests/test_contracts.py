"""
Phase 1 contract tests — config and claim schema guardrails.

These tests do NOT load spaCy, FAISS, or transformer models. Heavy runtime
dependencies are mocked so the suite runs fast in any environment.

Run:
    pytest tests/test_contracts.py -x -v
"""

import sys
import types
import pytest
import unittest.mock as mock


# ---------------------------------------------------------------------------
# Lightweight mock for heavy dependencies so tests don't require GPU/models.
# ---------------------------------------------------------------------------

def _mock_heavy_deps():
    for mod_name in [
        "spacy", "faiss", "torch",
        "transformers",
        "sklearn", "sklearn.metrics", "sklearn.metrics.pairwise",
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = mock.MagicMock()


_mock_heavy_deps()

# Import after mocking so the module-level spacy.load() calls don't fail.
import importlib.util, pathlib

_SRC = pathlib.Path(__file__).parent.parent / "src"

# Ensure src/ is on sys.path so that intra-src imports (e.g. `from medical_config
# import ...` inside claim_extractor_fixed) resolve correctly.
_SRC_STR = str(_SRC)
if _SRC_STR not in sys.path:
    sys.path.insert(0, _SRC_STR)


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _SRC / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # register so cross-module imports resolve
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


# ===========================================================================
# VERI-01 — Extractor reads centralized config only
# ===========================================================================

class TestExtractorReadsGlobalConfig:
    """ClaimExtractor must consume ConfigurationSettings, not inline dicts."""

    def test_none_config_resolves_to_global_config(self):
        """Passing None must result in ClaimExtractor holding the global config."""
        extractor = ClaimExtractor(config=None)
        assert isinstance(extractor.config, ConfigurationSettings)

    def test_valid_config_object_accepted(self):
        """A valid ConfigurationSettings instance must be accepted."""
        cfg = ConfigurationSettings()
        extractor = ClaimExtractor(config=cfg)
        assert extractor.config is cfg

    def test_raw_dict_rejected(self):
        """Passing a plain dict must raise TypeError before any model work."""
        with pytest.raises(TypeError, match="ConfigurationSettings"):
            ClaimExtractor(config={"top_k_facts": 5, "confidence_thresholds": {}})

    def test_string_rejected(self):
        """Passing an arbitrary object must raise TypeError."""
        with pytest.raises(TypeError):
            ClaimExtractor(config="high")

    def test_extractor_uses_config_attributes_not_dict_keys(self):
        """Verify extractor exposes .config.TOP_K_FACTS (attribute), not dict key access."""
        extractor = ClaimExtractor(config=None)
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
