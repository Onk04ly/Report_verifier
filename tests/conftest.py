"""
Shared fixtures for Phase 1 contract tests.

Provides canonical claim payload examples, invalid claim examples,
and a deterministic verification result payload used across test modules.

Heavy runtime dependencies (spaCy models, FAISS, transformer weights, pandas
CSV loading) are patched here so that contract tests run without requiring the
full data pipeline to be initialized.
"""

import os
import json
import sys
import types
import unittest.mock as mock
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Patch heavy dependencies at import time so _load_module() calls in
# test_contracts.py do not trigger real model loading.
# ---------------------------------------------------------------------------

def _install_module_mock(name: str):
    """Register a MagicMock in sys.modules for *name* if not already present."""
    if name not in sys.modules:
        sys.modules[name] = mock.MagicMock()


_HEAVY_MODULES = [
    "spacy",
    "faiss",
    "torch",
    "transformers",
    "sklearn",
    "sklearn.metrics",
    "sklearn.metrics.pairwise",
]

for _mod in _HEAVY_MODULES:
    _install_module_mock(_mod)


# ---------------------------------------------------------------------------
# Canonical claim payload shapes
# ---------------------------------------------------------------------------

#: Minimal set of keys every valid claim dict must contain.
REQUIRED_CLAIM_KEYS = frozenset({
    "claim_text",
    "type",
    "medical_entities",
    "verification_confidence",
    "verification_score",
})


def _make_valid_claim(**overrides) -> dict:
    """Return a claim dict that satisfies the canonical schema."""
    base = {
        "claim_text": "Metformin is the first-line treatment for type 2 diabetes.",
        "type": "treatment",
        "medical_entities": ["metformin", "type 2 diabetes"],
        "verification_confidence": "HIGH",
        "verification_score": 0.85,
        "has_negation": False,
        "has_uncertainty": False,
        "certainty_modifier": "positive",
    }
    base.update(overrides)
    return base


def _make_invalid_claim_missing_claim_text() -> dict:
    """Return a claim that uses the legacy 'text' key instead of 'claim_text'."""
    claim = _make_valid_claim()
    del claim["claim_text"]
    claim["text"] = claim.get("claim_text", "some legacy text")
    return claim


# ---------------------------------------------------------------------------
# Deterministic verification result payload
# ---------------------------------------------------------------------------

def _make_verification_result(summary_id: str = "test_summary_001") -> dict:
    """Return a deterministic verification result with the expected export shape."""
    return {
        "summary_id": summary_id,
        "original_text": "Metformin is the first-line treatment for type 2 diabetes.",
        "sentences": ["Metformin is the first-line treatment for type 2 diabetes."],
        "claims": [_make_valid_claim()],
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
            "safety_recommendations": [
                "Cross-reference all medical claims with authoritative medical literature",
                "Consult qualified healthcare professionals for clinical decisions",
                "Use this analysis as a quality assurance tool, not diagnostic guidance",
            ],
            "requires_expert_review": False,
            "auto_flagged": False,
            "disclaimer": {
                "title": "RESPONSIBLE AI - HEALTHCARE SAFETY NOTICE",
                "notice": [],
                "limitations": [],
                "proper_use": [],
            },
            "safety_assessment": {
                "low_confidence_ratio": 0.0,
                "safety_threshold_exceeded": False,
                "critical_threshold_exceeded": False,
                "contains_medical_terms": True,
                "contains_dangerous_terms": False,
                "dangerous_terms_detected": [],
            },
        },
    }


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_claim() -> dict:
    """A single claim dict that satisfies the canonical claim_text schema."""
    return _make_valid_claim()


@pytest.fixture()
def valid_claims_list() -> list:
    """A list of two valid claim dicts for batch-flow tests."""
    return [
        _make_valid_claim(
            claim_text="Metformin is the first-line treatment for type 2 diabetes.",
            verification_confidence="HIGH",
            verification_score=0.85,
        ),
        _make_valid_claim(
            claim_text="Insulin is required for type 1 diabetes management.",
            verification_confidence="MEDIUM",
            verification_score=0.55,
        ),
    ]


@pytest.fixture()
def invalid_claim_missing_claim_text() -> dict:
    """A claim dict that uses the legacy 'text' key — must be rejected."""
    claim = _make_valid_claim()
    del claim["claim_text"]
    claim["text"] = "some legacy text"
    return claim


@pytest.fixture()
def invalid_claim_empty() -> dict:
    """A completely empty claim dict — must be rejected."""
    return {}


@pytest.fixture()
def deterministic_verification_result() -> dict:
    """A fully populated, deterministic verification result for export tests."""
    return _make_verification_result()


@pytest.fixture()
def deterministic_verification_result_list() -> list:
    """Two deterministic verification results for batch export tests."""
    return [
        _make_verification_result("test_summary_001"),
        _make_verification_result("test_summary_002"),
    ]


# ---------------------------------------------------------------------------
# Phase 2 Safety Guardrail Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeds_json_path():
    """Absolute path to the seeds JSON shipped with the repo."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data',
        'dangerous_guidance_seeds.json'
    )


@pytest.fixture
def oversized_input():
    """String strictly longer than the default MAX_SUMMARY_CHARS=5000."""
    return "The patient has diabetes. " * 400  # ~10,400 chars


@pytest.fixture
def duplicate_heavy_input():
    """Text whose duplicate-sentence ratio > 0.5."""
    sentence = "The patient has diabetes."
    unique = "The patient was admitted yesterday."
    return (sentence + " ") * 10 + unique  # 10 duplicates + 1 unique = ratio ~0.91


@pytest.fixture
def dangerous_claim_text():
    """Claim phrased like a seeded dangerous-guidance entry."""
    return "Patients should stop taking their insulin without medical supervision."


@pytest.fixture
def safe_clinical_text():
    """Neutral clinical text that must NOT trip the semantic danger check."""
    return "The patient was counseled on proper insulin administration techniques."


@pytest.fixture
def mock_verifier_no_models():
    """
    Build a MedicalVerifier whose extractor has sentence_model=None to
    exercise the SAFE-03 degraded-mode branch.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
    from medical_verifier import MedicalVerifier
    from claim_extractor_fixed import ClaimExtractor

    with (
        mock.patch("claim_extractor_fixed.spacy.load", return_value=mock.MagicMock()),
        mock.patch("claim_extractor_fixed.hf_pipeline", return_value=mock.MagicMock()),
        mock.patch("claim_extractor_fixed.SentenceTransformer", return_value=None),
        mock.patch.object(ClaimExtractor, "_init_retriever", return_value=None),
    ):
        verifier = MedicalVerifier()
        verifier.extractor.sentence_model = None
        verifier.extractor.danger_centroid = None
        verifier.extractor._seeds_file_status = 'missing'
        return verifier
