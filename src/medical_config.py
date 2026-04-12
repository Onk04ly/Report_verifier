"""
Medical Verification Configuration
==================================

Centralized configuration for the Medical Report Verification System.
All threshold values and parameters are defined here and validated at
construction time. No module may define its own inline runtime defaults
for thresholds or scoring constants.

Usage:
    from medical_config import get_global_config

    config = get_global_config()
    thresholds = config.get_confidence_thresholds()
    params = config.get_extraction_params()
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ConfigurationSettings:
    """
    Single source of truth for Medical Verification runtime configuration.

    All fields are validated in __post_init__. Construction raises ValueError
    immediately if any required invariant is violated, so invalid config
    cannot propagate into extraction or scoring logic.
    """

    # ------------------------------------------------------------------ #
    # Confidence thresholds
    # ------------------------------------------------------------------ #
    CONFIDENCE_HIGH: float = 0.30       # Claims above this = HIGH confidence
    CONFIDENCE_MEDIUM: float = 0.22     # Claims above this = MEDIUM confidence
    # Claims below CONFIDENCE_MEDIUM = LOW confidence

    # ------------------------------------------------------------------ #
    # Safety and risk assessment thresholds
    # ------------------------------------------------------------------ #
    HIGH_RISK_THRESHOLD: float = 0.30           # Flag as HIGH RISK
    CRITICAL_THRESHOLD: float = 0.50            # Flag as CRITICAL
    EXPERT_REVIEW_THRESHOLD: float = 0.20       # Expert review required
    AUTO_FLAG_THRESHOLD: float = 0.40           # Auto-flag for QA

    # ------------------------------------------------------------------ #
    # Risk assessment ratios
    # ------------------------------------------------------------------ #
    HIGH_RISK_LOW_CONF_RATIO: float = 0.50     # 50%+ low confidence = HIGH RISK
    MEDIUM_RISK_LOW_CONF_RATIO: float = 0.30   # 30%+ low confidence = MEDIUM RISK
    LOW_RISK_HIGH_CONF_RATIO: float = 0.40     # 40%+ high confidence = LOW RISK
    HIGH_NEGATION_RATIO: float = 0.30          # 30%+ negation = risk factor
    HIGH_UNCERTAINTY_RATIO: float = 0.50       # 50%+ uncertainty = risk factor

    # ------------------------------------------------------------------ #
    # Evidence quality thresholds
    # ------------------------------------------------------------------ #
    HIGH_QUALITY_SCORE: float = 0.70           # Quality score > 0.7 = high quality
    MEDIUM_QUALITY_MIN: float = 0.40           # Quality score 0.4-0.7 = medium
    MEDIUM_QUALITY_MAX: float = 0.70

    # ------------------------------------------------------------------ #
    # Evidence weights for confidence scoring
    # ------------------------------------------------------------------ #
    SIMILARITY_AVG_WEIGHT: float = 0.40        # Weight for average similarity
    SIMILARITY_MAX_WEIGHT: float = 0.20        # Weight for max similarity
    DISTANCE_WEIGHT: float = 0.20              # Weight for distance metric
    EVIDENCE_QUALITY_WEIGHT: float = 0.20      # Weight for evidence quality

    # ------------------------------------------------------------------ #
    # Extraction parameters
    # ------------------------------------------------------------------ #
    TOP_K_FACTS: int = 5                       # Top facts to retrieve per claim
    CONFIDENCE_FACTS_COUNT: int = 3            # Facts used for confidence calculation
    MIN_SENTENCE_LENGTH: int = 8               # Minimum sentence length to process
    MAX_CLAIMS_PER_SUMMARY: int = 50           # Maximum claims per summary

    # ------------------------------------------------------------------ #
    # Extractor distance normalization and penalty constants
    # These were previously hardcoded inline in ClaimExtractor; they now
    # live here so all scoring behavior is auditable from one place.
    # ------------------------------------------------------------------ #

    # Distance normalization divisor used in confidence scoring:
    #   normalized_distance_score = max(0, 1 - (avg_distance / DISTANCE_NORM_DIVISOR))
    DISTANCE_NORM_DIVISOR: float = 100.0

    # Outlier penalty: only penalise claims whose nearest KB match exceeds
    # this distance threshold (FAISS L2 space).
    OUTLIER_DISTANCE_THRESHOLD: float = 35.0

    # Linear penalty scaling applied per unit of distance beyond threshold:
    #   penalty = OUTLIER_PENALTY_BASE + (distance - threshold) * OUTLIER_PENALTY_SCALING
    OUTLIER_PENALTY_BASE: float = 0.2
    OUTLIER_PENALTY_SCALING: float = 0.005

    # Maximum outlier penalty that can be applied (cap).
    OUTLIER_PENALTY_CAP: float = 0.4

    # ------------------------------------------------------------------ #
    # __post_init__ validation
    # ------------------------------------------------------------------ #
    def __post_init__(self) -> None:
        """
        Validate all configuration invariants at construction time.

        Raises ValueError listing every invalid key and its bad value so
        callers receive a complete diagnostic without needing to re-run.
        """
        errors: list[str] = []

        def _check_probability(name: str, value: float) -> None:
            if not isinstance(value, (int, float)):
                errors.append(f"{name}={value!r}: must be a number")
            elif not (0.0 <= value <= 1.0):
                errors.append(f"{name}={value}: must be in [0.0, 1.0]")

        def _check_positive_float(name: str, value: float) -> None:
            if not isinstance(value, (int, float)):
                errors.append(f"{name}={value!r}: must be a number")
            elif value <= 0.0:
                errors.append(f"{name}={value}: must be > 0.0")

        def _check_positive_int(name: str, value: int) -> None:
            if not isinstance(value, int):
                errors.append(f"{name}={value!r}: must be an integer")
            elif value <= 0:
                errors.append(f"{name}={value}: must be > 0")

        # Confidence thresholds
        _check_probability("CONFIDENCE_HIGH", self.CONFIDENCE_HIGH)
        _check_probability("CONFIDENCE_MEDIUM", self.CONFIDENCE_MEDIUM)
        if (isinstance(self.CONFIDENCE_HIGH, (int, float)) and
                isinstance(self.CONFIDENCE_MEDIUM, (int, float)) and
                self.CONFIDENCE_MEDIUM >= self.CONFIDENCE_HIGH):
            errors.append(
                f"CONFIDENCE_MEDIUM={self.CONFIDENCE_MEDIUM} must be < "
                f"CONFIDENCE_HIGH={self.CONFIDENCE_HIGH}"
            )

        # Safety thresholds
        _check_probability("HIGH_RISK_THRESHOLD", self.HIGH_RISK_THRESHOLD)
        _check_probability("CRITICAL_THRESHOLD", self.CRITICAL_THRESHOLD)
        _check_probability("EXPERT_REVIEW_THRESHOLD", self.EXPERT_REVIEW_THRESHOLD)
        _check_probability("AUTO_FLAG_THRESHOLD", self.AUTO_FLAG_THRESHOLD)

        # Risk ratios
        _check_probability("HIGH_RISK_LOW_CONF_RATIO", self.HIGH_RISK_LOW_CONF_RATIO)
        _check_probability("MEDIUM_RISK_LOW_CONF_RATIO", self.MEDIUM_RISK_LOW_CONF_RATIO)
        _check_probability("LOW_RISK_HIGH_CONF_RATIO", self.LOW_RISK_HIGH_CONF_RATIO)
        _check_probability("HIGH_NEGATION_RATIO", self.HIGH_NEGATION_RATIO)
        _check_probability("HIGH_UNCERTAINTY_RATIO", self.HIGH_UNCERTAINTY_RATIO)

        # Evidence quality
        _check_probability("HIGH_QUALITY_SCORE", self.HIGH_QUALITY_SCORE)
        _check_probability("MEDIUM_QUALITY_MIN", self.MEDIUM_QUALITY_MIN)
        _check_probability("MEDIUM_QUALITY_MAX", self.MEDIUM_QUALITY_MAX)

        # Evidence weights
        _check_probability("SIMILARITY_AVG_WEIGHT", self.SIMILARITY_AVG_WEIGHT)
        _check_probability("SIMILARITY_MAX_WEIGHT", self.SIMILARITY_MAX_WEIGHT)
        _check_probability("DISTANCE_WEIGHT", self.DISTANCE_WEIGHT)
        _check_probability("EVIDENCE_QUALITY_WEIGHT", self.EVIDENCE_QUALITY_WEIGHT)

        weight_sum = (
            self.SIMILARITY_AVG_WEIGHT + self.SIMILARITY_MAX_WEIGHT +
            self.DISTANCE_WEIGHT + self.EVIDENCE_QUALITY_WEIGHT
        )
        # Allow a small floating-point tolerance
        if abs(weight_sum - 1.0) > 1e-6:
            errors.append(
                f"Evidence weights must sum to 1.0 (got {weight_sum:.6f}): "
                f"SIMILARITY_AVG_WEIGHT={self.SIMILARITY_AVG_WEIGHT}, "
                f"SIMILARITY_MAX_WEIGHT={self.SIMILARITY_MAX_WEIGHT}, "
                f"DISTANCE_WEIGHT={self.DISTANCE_WEIGHT}, "
                f"EVIDENCE_QUALITY_WEIGHT={self.EVIDENCE_QUALITY_WEIGHT}"
            )

        # Extraction parameters
        _check_positive_int("TOP_K_FACTS", self.TOP_K_FACTS)
        _check_positive_int("CONFIDENCE_FACTS_COUNT", self.CONFIDENCE_FACTS_COUNT)
        _check_positive_int("MIN_SENTENCE_LENGTH", self.MIN_SENTENCE_LENGTH)
        _check_positive_int("MAX_CLAIMS_PER_SUMMARY", self.MAX_CLAIMS_PER_SUMMARY)

        # Distance / outlier constants
        _check_positive_float("DISTANCE_NORM_DIVISOR", self.DISTANCE_NORM_DIVISOR)
        _check_positive_float("OUTLIER_DISTANCE_THRESHOLD", self.OUTLIER_DISTANCE_THRESHOLD)
        _check_probability("OUTLIER_PENALTY_BASE", self.OUTLIER_PENALTY_BASE)
        _check_positive_float("OUTLIER_PENALTY_SCALING", self.OUTLIER_PENALTY_SCALING)
        _check_probability("OUTLIER_PENALTY_CAP", self.OUTLIER_PENALTY_CAP)

        if errors:
            joined = "\n  ".join(errors)
            raise ValueError(
                f"ConfigurationSettings has {len(errors)} invalid field(s):\n  {joined}"
            )

    # ------------------------------------------------------------------ #
    # Accessor methods
    # ------------------------------------------------------------------ #
    def get_confidence_thresholds(self) -> Dict[str, float]:
        """Return confidence thresholds as a dictionary."""
        return {
            'high': self.CONFIDENCE_HIGH,
            'medium': self.CONFIDENCE_MEDIUM,
        }

    def get_safety_config(self) -> Dict[str, float]:
        """Return safety configuration."""
        return {
            'high_risk_threshold': self.HIGH_RISK_THRESHOLD,
            'critical_threshold': self.CRITICAL_THRESHOLD,
            'require_expert_review_threshold': self.EXPERT_REVIEW_THRESHOLD,
            'auto_flag_threshold': self.AUTO_FLAG_THRESHOLD,
        }

    def get_risk_thresholds(self) -> Dict[str, float]:
        """Return risk assessment thresholds."""
        return {
            'high_risk_low_conf_ratio': self.HIGH_RISK_LOW_CONF_RATIO,
            'medium_risk_low_conf_ratio': self.MEDIUM_RISK_LOW_CONF_RATIO,
            'low_risk_high_conf_ratio': self.LOW_RISK_HIGH_CONF_RATIO,
            'high_negation_ratio': self.HIGH_NEGATION_RATIO,
            'high_uncertainty_ratio': self.HIGH_UNCERTAINTY_RATIO,
        }

    def get_evidence_weights(self) -> Dict[str, float]:
        """Return evidence weights for confidence scoring."""
        return {
            'similarity_avg': self.SIMILARITY_AVG_WEIGHT,
            'similarity_max': self.SIMILARITY_MAX_WEIGHT,
            'distance': self.DISTANCE_WEIGHT,
            'evidence_quality': self.EVIDENCE_QUALITY_WEIGHT,
        }

    def get_extraction_params(self) -> Dict[str, int]:
        """Return extraction parameters."""
        return {
            'top_k_facts': self.TOP_K_FACTS,
            'confidence_facts_count': self.CONFIDENCE_FACTS_COUNT,
            'min_sentence_length': self.MIN_SENTENCE_LENGTH,
            'max_claims_per_summary': self.MAX_CLAIMS_PER_SUMMARY,
        }

    def get_outlier_params(self) -> Dict[str, float]:
        """Return distance normalization and outlier penalty parameters."""
        return {
            'distance_norm_divisor': self.DISTANCE_NORM_DIVISOR,
            'outlier_distance_threshold': self.OUTLIER_DISTANCE_THRESHOLD,
            'outlier_penalty_base': self.OUTLIER_PENALTY_BASE,
            'outlier_penalty_scaling': self.OUTLIER_PENALTY_SCALING,
            'outlier_penalty_cap': self.OUTLIER_PENALTY_CAP,
        }

    def print_config(self) -> None:
        """Print current configuration values."""
        print("\n=== Medical Verification Configuration ===")
        print("Confidence Thresholds:")
        print(f"  High:   {self.CONFIDENCE_HIGH}")
        print(f"  Medium: {self.CONFIDENCE_MEDIUM}")
        print("Safety Thresholds:")
        print(f"  High Risk:     {self.HIGH_RISK_THRESHOLD}")
        print(f"  Critical:      {self.CRITICAL_THRESHOLD}")
        print(f"  Expert Review: {self.EXPERT_REVIEW_THRESHOLD}")
        print("Extraction Parameters:")
        print(f"  Top K Facts:      {self.TOP_K_FACTS}")
        print(f"  Confidence Facts: {self.CONFIDENCE_FACTS_COUNT}")
        print("Outlier / Distance Constants:")
        print(f"  Norm Divisor:         {self.DISTANCE_NORM_DIVISOR}")
        print(f"  Outlier Threshold:    {self.OUTLIER_DISTANCE_THRESHOLD}")
        print(f"  Penalty Base:         {self.OUTLIER_PENALTY_BASE}")
        print(f"  Penalty Scaling:      {self.OUTLIER_PENALTY_SCALING}")
        print(f"  Penalty Cap:          {self.OUTLIER_PENALTY_CAP}")
        print("=" * 45)


# ------------------------------------------------------------------ #
# Module-level singleton
# ------------------------------------------------------------------ #

# Validate at import time — any bad default is caught immediately.
config = ConfigurationSettings()


def get_global_config() -> ConfigurationSettings:
    """Return the validated global configuration instance."""
    return config


# Convenience helpers kept for callers that import them directly.
def get_confidence_thresholds() -> Dict[str, float]:
    """Return confidence thresholds."""
    return config.get_confidence_thresholds()


def get_safety_config() -> Dict[str, float]:
    """Return safety configuration."""
    return config.get_safety_config()


def get_risk_thresholds() -> Dict[str, float]:
    """Return risk assessment thresholds."""
    return config.get_risk_thresholds()


if __name__ == "__main__":
    config.print_config()
