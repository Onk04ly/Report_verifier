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
    # Phase 2 — Safety and guardrail hardening (SAFE-01, SAFE-02)
    # Added to centralize runtime input-validation and semantic danger
    # detection tunables. Read via get_global_config(); never hardcode.
    # ------------------------------------------------------------------ #
    DANGEROUS_SEMANTIC_THRESHOLD: float = 0.75  # Cosine similarity cutoff for dangerous-guidance centroid match (SAFE-01)
    MAX_SUMMARY_CHARS: int = 5000               # Hard truncation limit for input summaries (SAFE-02a)
    DUPLICATE_SENTENCE_RATIO: float = 0.5       # Fraction of duplicate sentences to flag as repeated_content (SAFE-02a)

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
    # Evidence grade weights for confidence scoring
    # Used in calculate_confidence_score to translate letter grades to
    # numeric quality multipliers.
    # ------------------------------------------------------------------ #
    GRADE_WEIGHT_A: float = 1.0   # Grade A evidence (highest quality)
    GRADE_WEIGHT_B: float = 0.8   # Grade B evidence
    GRADE_WEIGHT_C: float = 0.6   # Grade C evidence
    GRADE_WEIGHT_D: float = 0.4   # Grade D evidence (lowest quality)

    # ------------------------------------------------------------------ #
    # Plausibility penalty values used in _check_*_optimized sub-methods.
    # These map to named severity levels; numeric values preserved exactly.
    # ------------------------------------------------------------------ #
    PLAUSIBILITY_PENALTY_CRITICAL: float = 1.0   # Absolute impossibility
    PLAUSIBILITY_PENALTY_VERY_HIGH: float = 0.95  # Near-certain violation
    PLAUSIBILITY_PENALTY_HIGH: float = 0.9        # Strong implausibility
    PLAUSIBILITY_PENALTY_MEDIUM_HIGH: float = 0.8 # Moderate-high implausibility
    PLAUSIBILITY_PENALTY_MEDIUM: float = 0.7      # Moderate implausibility
    PLAUSIBILITY_PENALTY_LOW: float = 0.6         # Mild implausibility

    # ------------------------------------------------------------------ #
    # Evidence absence penalty constants used in _detect_evidence_absence_penalty.
    # Distance cutoffs (FAISS L2 space); penalty multipliers applied when
    # supporting evidence quality is insufficient.
    # ------------------------------------------------------------------ #
    EVIDENCE_ABSENCE_PENALTY_NO_FACTS: float = 0.8    # No supporting facts at all
    EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_2: float = 0.4 # Two or more C/D grade facts
    EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_1: float = 0.2 # One C/D grade fact
    EVIDENCE_ABSENCE_DIST_CRITICAL: float = 25.0      # avg distance > this: high penalty
    EVIDENCE_ABSENCE_PENALTY_DIST_HIGH: float = 0.5   # Penalty for avg dist > CRITICAL
    EVIDENCE_ABSENCE_DIST_HIGH: float = 20.0          # avg distance > this: medium penalty
    EVIDENCE_ABSENCE_PENALTY_DIST_MEDIUM: float = 0.3 # Penalty for avg dist > HIGH
    EVIDENCE_ABSENCE_DIST_ALL_IRRELEVANT: float = 30.0 # All facts beyond this = irrelevant
    EVIDENCE_ABSENCE_PENALTY_ALL_IRRELEVANT: float = 0.7 # Penalty when all facts irrelevant

    # ------------------------------------------------------------------ #
    # Negation and uncertainty confidence multipliers used in
    # identify_medical_claims to adjust final base_confidence values.
    # ------------------------------------------------------------------ #
    NEGATION_CONFIDENCE_BASE_HIGH: float = 0.8   # Base confidence for non-entity claims
    NEGATION_CONFIDENCE_BASE_LOW: float = 0.6    # Base confidence for entity_based claims
    NEGATION_CONFIDENCE_PENALTY: float = 0.7     # Multiplier applied when has_negation
    UNCERTAINTY_CONFIDENCE_PENALTY: float = 0.6  # Multiplier applied when has_uncertainty

    # ------------------------------------------------------------------ #
    # Phase 5 — Disease Scope Specialization (FOCUS-01, D-01 to D-06)
    # Disease set is locked to these two slugs. Add new diseases only after
    # expansion gate passes (see EXPANSION_GATE_N, EXPANSION_GATE_CONSECUTIVE).
    # ------------------------------------------------------------------ #
    DISEASE_LIST: list = field(default_factory=lambda: ["type1_diabetes", "metastatic_cancer"])
    DISEASE_CENTROID_SIM_THRESHOLD: float = 0.60   # Min cosine sim for KB bucket assignment (D-04)
    DISEASE_CENTROID_TOP_K: int = 20               # Top-K quality articles for centroid (D-04)
    EXPANSION_GATE_N: int = 5                      # Evaluate gate every N pipeline runs (D-06)
    EXPANSION_GATE_CONSECUTIVE: int = 2            # Consecutive passing runs required (D-03/D-06)
    DISEASE_RANDOM_SEED: int = 42                  # Fixed seed for dataset splits (D-05)
    DISEASE_PRECISION_TARGET: float = 0.65         # Per-disease precision target (D-03)
    DISEASE_ACCURACY_TARGET: float = 0.60          # Per-disease accuracy target (D-03)
    HOLDOUT_FRACTION: float = 0.20                 # 20% holdout per D-05
    TUNE_FRACTION: float = 0.20                    # 20% tune set per D-05
    TRAIN_FRACTION: float = 0.60                   # 60% train set per D-05

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

        # Phase 2 additions
        _check_probability("DANGEROUS_SEMANTIC_THRESHOLD", self.DANGEROUS_SEMANTIC_THRESHOLD)
        _check_probability("DUPLICATE_SENTENCE_RATIO", self.DUPLICATE_SENTENCE_RATIO)
        _check_positive_int("MAX_SUMMARY_CHARS", self.MAX_SUMMARY_CHARS)

        # Distance / outlier constants
        _check_positive_float("DISTANCE_NORM_DIVISOR", self.DISTANCE_NORM_DIVISOR)
        _check_positive_float("OUTLIER_DISTANCE_THRESHOLD", self.OUTLIER_DISTANCE_THRESHOLD)
        _check_probability("OUTLIER_PENALTY_BASE", self.OUTLIER_PENALTY_BASE)
        _check_positive_float("OUTLIER_PENALTY_SCALING", self.OUTLIER_PENALTY_SCALING)
        _check_probability("OUTLIER_PENALTY_CAP", self.OUTLIER_PENALTY_CAP)

        # Evidence grade weights
        _check_probability("GRADE_WEIGHT_A", self.GRADE_WEIGHT_A)
        _check_probability("GRADE_WEIGHT_B", self.GRADE_WEIGHT_B)
        _check_probability("GRADE_WEIGHT_C", self.GRADE_WEIGHT_C)
        _check_probability("GRADE_WEIGHT_D", self.GRADE_WEIGHT_D)

        # Plausibility penalty values
        _check_probability("PLAUSIBILITY_PENALTY_CRITICAL", self.PLAUSIBILITY_PENALTY_CRITICAL)
        _check_probability("PLAUSIBILITY_PENALTY_VERY_HIGH", self.PLAUSIBILITY_PENALTY_VERY_HIGH)
        _check_probability("PLAUSIBILITY_PENALTY_HIGH", self.PLAUSIBILITY_PENALTY_HIGH)
        _check_probability("PLAUSIBILITY_PENALTY_MEDIUM_HIGH", self.PLAUSIBILITY_PENALTY_MEDIUM_HIGH)
        _check_probability("PLAUSIBILITY_PENALTY_MEDIUM", self.PLAUSIBILITY_PENALTY_MEDIUM)
        _check_probability("PLAUSIBILITY_PENALTY_LOW", self.PLAUSIBILITY_PENALTY_LOW)

        # Evidence absence penalty constants
        _check_probability("EVIDENCE_ABSENCE_PENALTY_NO_FACTS", self.EVIDENCE_ABSENCE_PENALTY_NO_FACTS)
        _check_probability("EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_2", self.EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_2)
        _check_probability("EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_1", self.EVIDENCE_ABSENCE_PENALTY_LOW_GRADE_1)
        _check_positive_float("EVIDENCE_ABSENCE_DIST_CRITICAL", self.EVIDENCE_ABSENCE_DIST_CRITICAL)
        _check_probability("EVIDENCE_ABSENCE_PENALTY_DIST_HIGH", self.EVIDENCE_ABSENCE_PENALTY_DIST_HIGH)
        _check_positive_float("EVIDENCE_ABSENCE_DIST_HIGH", self.EVIDENCE_ABSENCE_DIST_HIGH)
        _check_probability("EVIDENCE_ABSENCE_PENALTY_DIST_MEDIUM", self.EVIDENCE_ABSENCE_PENALTY_DIST_MEDIUM)
        _check_positive_float("EVIDENCE_ABSENCE_DIST_ALL_IRRELEVANT", self.EVIDENCE_ABSENCE_DIST_ALL_IRRELEVANT)
        _check_probability("EVIDENCE_ABSENCE_PENALTY_ALL_IRRELEVANT", self.EVIDENCE_ABSENCE_PENALTY_ALL_IRRELEVANT)

        # Negation / uncertainty confidence multipliers
        _check_probability("NEGATION_CONFIDENCE_BASE_HIGH", self.NEGATION_CONFIDENCE_BASE_HIGH)
        _check_probability("NEGATION_CONFIDENCE_BASE_LOW", self.NEGATION_CONFIDENCE_BASE_LOW)
        _check_probability("NEGATION_CONFIDENCE_PENALTY", self.NEGATION_CONFIDENCE_PENALTY)
        _check_probability("UNCERTAINTY_CONFIDENCE_PENALTY", self.UNCERTAINTY_CONFIDENCE_PENALTY)

        # Phase 5 disease config
        if not isinstance(self.DISEASE_LIST, list) or len(self.DISEASE_LIST) < 1:
            errors.append("DISEASE_LIST must be a non-empty list")
        _check_probability("DISEASE_CENTROID_SIM_THRESHOLD", self.DISEASE_CENTROID_SIM_THRESHOLD)
        _check_positive_int("DISEASE_CENTROID_TOP_K", self.DISEASE_CENTROID_TOP_K)
        _check_positive_int("EXPANSION_GATE_N", self.EXPANSION_GATE_N)
        _check_positive_int("EXPANSION_GATE_CONSECUTIVE", self.EXPANSION_GATE_CONSECUTIVE)
        if not isinstance(self.DISEASE_RANDOM_SEED, int):
            errors.append("DISEASE_RANDOM_SEED must be an integer")
        _check_probability("DISEASE_PRECISION_TARGET", self.DISEASE_PRECISION_TARGET)
        _check_probability("DISEASE_ACCURACY_TARGET", self.DISEASE_ACCURACY_TARGET)
        _check_probability("HOLDOUT_FRACTION", self.HOLDOUT_FRACTION)
        _check_probability("TUNE_FRACTION", self.TUNE_FRACTION)
        _check_probability("TRAIN_FRACTION", self.TRAIN_FRACTION)
        split_sum = self.HOLDOUT_FRACTION + self.TUNE_FRACTION + self.TRAIN_FRACTION
        if abs(split_sum - 1.0) > 1e-6:
            errors.append(
                f"HOLDOUT_FRACTION + TUNE_FRACTION + TRAIN_FRACTION must sum to 1.0 (got {split_sum:.6f})"
            )

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

    def get_disease_config(self) -> Dict[str, Any]:
        """Return Phase 5 disease specialization config as a dictionary."""
        return {
            'disease_list': self.DISEASE_LIST,
            'centroid_sim_threshold': self.DISEASE_CENTROID_SIM_THRESHOLD,
            'centroid_top_k': self.DISEASE_CENTROID_TOP_K,
            'expansion_gate_n': self.EXPANSION_GATE_N,
            'expansion_gate_consecutive': self.EXPANSION_GATE_CONSECUTIVE,
            'random_seed': self.DISEASE_RANDOM_SEED,
            'precision_target': self.DISEASE_PRECISION_TARGET,
            'accuracy_target': self.DISEASE_ACCURACY_TARGET,
            'holdout_fraction': self.HOLDOUT_FRACTION,
            'tune_fraction': self.TUNE_FRACTION,
            'train_fraction': self.TRAIN_FRACTION,
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

    def get_grade_weights(self) -> Dict[str, float]:
        """Return evidence grade letter-to-numeric weight mapping."""
        return {
            'A': self.GRADE_WEIGHT_A,
            'B': self.GRADE_WEIGHT_B,
            'C': self.GRADE_WEIGHT_C,
            'D': self.GRADE_WEIGHT_D,
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
