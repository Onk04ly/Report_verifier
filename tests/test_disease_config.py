"""
Tests for Phase 5 disease-specialization config block in ConfigurationSettings.

TDD — RED phase: these tests should fail before Task 1 implementation.
"""

import pytest
from src.medical_config import ConfigurationSettings, get_global_config


class TestDiseaseConfigFields:
    """Verify all Phase 5 disease-config fields are present with correct defaults."""

    def test_disease_list_default(self):
        cfg = ConfigurationSettings()
        assert cfg.DISEASE_LIST == ["type1_diabetes", "metastatic_cancer"]

    def test_disease_centroid_sim_threshold_default(self):
        cfg = ConfigurationSettings()
        assert cfg.DISEASE_CENTROID_SIM_THRESHOLD == 0.60

    def test_disease_centroid_top_k_default(self):
        cfg = ConfigurationSettings()
        assert cfg.DISEASE_CENTROID_TOP_K == 20

    def test_expansion_gate_n_default(self):
        cfg = ConfigurationSettings()
        assert cfg.EXPANSION_GATE_N == 5

    def test_expansion_gate_consecutive_default(self):
        cfg = ConfigurationSettings()
        assert cfg.EXPANSION_GATE_CONSECUTIVE == 2

    def test_disease_random_seed_default(self):
        cfg = ConfigurationSettings()
        assert cfg.DISEASE_RANDOM_SEED == 42

    def test_disease_precision_target_default(self):
        cfg = ConfigurationSettings()
        assert cfg.DISEASE_PRECISION_TARGET == 0.65

    def test_disease_accuracy_target_default(self):
        cfg = ConfigurationSettings()
        assert cfg.DISEASE_ACCURACY_TARGET == 0.60

    def test_holdout_fraction_default(self):
        cfg = ConfigurationSettings()
        assert cfg.HOLDOUT_FRACTION == 0.20

    def test_tune_fraction_default(self):
        cfg = ConfigurationSettings()
        assert cfg.TUNE_FRACTION == 0.20

    def test_train_fraction_default(self):
        cfg = ConfigurationSettings()
        assert cfg.TRAIN_FRACTION == 0.60

    def test_split_fractions_sum_to_one(self):
        cfg = ConfigurationSettings()
        total = cfg.HOLDOUT_FRACTION + cfg.TUNE_FRACTION + cfg.TRAIN_FRACTION
        assert abs(total - 1.0) < 1e-6


class TestDiseaseConfigAccessor:
    """Verify get_disease_config() returns all fields correctly."""

    def test_get_disease_config_returns_dict(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert isinstance(dc, dict)

    def test_get_disease_config_disease_list(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["disease_list"] == ["type1_diabetes", "metastatic_cancer"]

    def test_get_disease_config_centroid_sim_threshold(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["centroid_sim_threshold"] == 0.60

    def test_get_disease_config_centroid_top_k(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["centroid_top_k"] == 20

    def test_get_disease_config_expansion_gate_n(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["expansion_gate_n"] == 5

    def test_get_disease_config_expansion_gate_consecutive(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["expansion_gate_consecutive"] == 2

    def test_get_disease_config_random_seed(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["random_seed"] == 42

    def test_get_disease_config_precision_target(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["precision_target"] == 0.65

    def test_get_disease_config_accuracy_target(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["accuracy_target"] == 0.60

    def test_get_disease_config_holdout_fraction(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["holdout_fraction"] == 0.20

    def test_get_disease_config_tune_fraction(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["tune_fraction"] == 0.20

    def test_get_disease_config_train_fraction(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        assert dc["train_fraction"] == 0.60

    def test_get_disease_config_has_all_11_keys(self):
        cfg = ConfigurationSettings()
        dc = cfg.get_disease_config()
        expected_keys = {
            "disease_list", "centroid_sim_threshold", "centroid_top_k",
            "expansion_gate_n", "expansion_gate_consecutive", "random_seed",
            "precision_target", "accuracy_target",
            "holdout_fraction", "tune_fraction", "train_fraction",
        }
        assert expected_keys == set(dc.keys())

    def test_get_global_config_has_get_disease_config(self):
        cfg = get_global_config()
        dc = cfg.get_disease_config()
        assert dc["disease_list"] == ["type1_diabetes", "metastatic_cancer"]


class TestDiseaseConfigValidation:
    """Verify __post_init__ validation of Phase 5 fields."""

    def test_empty_disease_list_raises(self):
        with pytest.raises(ValueError, match="DISEASE_LIST"):
            ConfigurationSettings(DISEASE_LIST=[])

    def test_non_list_disease_list_raises(self):
        with pytest.raises(ValueError, match="DISEASE_LIST"):
            ConfigurationSettings(DISEASE_LIST="type1_diabetes")

    def test_invalid_centroid_sim_threshold_above_1_raises(self):
        with pytest.raises(ValueError, match="DISEASE_CENTROID_SIM_THRESHOLD"):
            ConfigurationSettings(DISEASE_CENTROID_SIM_THRESHOLD=1.5)

    def test_invalid_centroid_sim_threshold_negative_raises(self):
        with pytest.raises(ValueError, match="DISEASE_CENTROID_SIM_THRESHOLD"):
            ConfigurationSettings(DISEASE_CENTROID_SIM_THRESHOLD=-0.1)

    def test_invalid_centroid_top_k_zero_raises(self):
        with pytest.raises(ValueError, match="DISEASE_CENTROID_TOP_K"):
            ConfigurationSettings(DISEASE_CENTROID_TOP_K=0)

    def test_invalid_expansion_gate_n_zero_raises(self):
        with pytest.raises(ValueError, match="EXPANSION_GATE_N"):
            ConfigurationSettings(EXPANSION_GATE_N=0)

    def test_invalid_expansion_gate_consecutive_zero_raises(self):
        with pytest.raises(ValueError, match="EXPANSION_GATE_CONSECUTIVE"):
            ConfigurationSettings(EXPANSION_GATE_CONSECUTIVE=0)

    def test_non_integer_random_seed_raises(self):
        with pytest.raises(ValueError, match="DISEASE_RANDOM_SEED"):
            ConfigurationSettings(DISEASE_RANDOM_SEED=42.0)

    def test_split_fractions_not_summing_to_one_raises(self):
        with pytest.raises(ValueError, match="HOLDOUT_FRACTION"):
            ConfigurationSettings(HOLDOUT_FRACTION=0.5)

    def test_valid_custom_split_fractions(self):
        """Verify that a valid custom split that sums to 1.0 is accepted."""
        cfg = ConfigurationSettings(
            HOLDOUT_FRACTION=0.10,
            TUNE_FRACTION=0.10,
            TRAIN_FRACTION=0.80,
        )
        assert abs(cfg.HOLDOUT_FRACTION + cfg.TUNE_FRACTION + cfg.TRAIN_FRACTION - 1.0) < 1e-6
