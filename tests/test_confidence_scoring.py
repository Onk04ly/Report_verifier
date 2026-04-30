"""
Phase 3 — TEST-03: Confidence score computation regression tests.

Covers ClaimExtractor.calculate_confidence_score() label/score contract:
  - Returns (label, score) tuple
  - label in {'HIGH', 'MEDIUM', 'LOW'}
  - score in [0.0, 1.0]
  - High-similarity supporting facts (identical embeddings + grade-A) → 'HIGH' label
  - Absent supporting facts → 'LOW' label
  - Orthogonal / low-quality facts → label != 'HIGH'
  - Mixed facts → label always in valid set, score always in [0.0, 1.0]

The conftest.py session-wide mock for sklearn.metrics.pairwise makes the
module-level `cosine_similarity` import in claim_extractor_fixed return a
MagicMock. Tests resolve this by patching
`claim_extractor_fixed.cosine_similarity` locally with a numpy-based
replacement (per D-08 / RESEARCH.md Pattern 4).
"""
import os
import sys
import unittest.mock as mock

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

import claim_extractor_fixed  # noqa: E402  -- module reference for patching
from claim_extractor_fixed import ClaimExtractor  # noqa: E402
from medical_config import get_global_config  # noqa: E402


# ---------------------------------------------------------------------------
# Numpy-based cosine similarity replacement
# ---------------------------------------------------------------------------

def _np_cosine_sim(a, b):
    """Numpy replacement for sklearn cosine_similarity.

    Returns shape (1, 1) ndarray to match sklearn's contract so downstream
    indexing via [0][0] in calculate_confidence_score is unchanged.
    """
    a_flat = np.asarray(a).flatten()
    b_flat = np.asarray(b).flatten()
    denom = np.linalg.norm(a_flat) * np.linalg.norm(b_flat)
    val = float(np.dot(a_flat, b_flat) / denom) if denom > 0 else 0.0
    return np.array([[val]])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_extractor_with_fixed_embedding(embedding):
    """Return a ClaimExtractor shell with get_sentence_embedding returning a fixed vector."""
    e = ClaimExtractor.__new__(ClaimExtractor)
    e.config = get_global_config()
    e.get_sentence_embedding = mock.MagicMock(return_value=embedding)
    return e


def _unit_vector(seed=0, dim=768):
    """Return a reproducible unit vector of the given dimension."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    """TEST-03: calculate_confidence_score() label/score contract.

    All tests patch claim_extractor_fixed.cosine_similarity locally so the
    globally mocked sklearn does not return MagicMock values during scoring.
    """

    def test_high_similarity_facts_yield_high_label(self):
        """Identical claim/fact embeddings + grade-A facts must yield label='HIGH'.

        With cosine_sim == 1.0 and high quality metrics the composite score should
        comfortably exceed the HIGH threshold (0.30).
        """
        emb = _unit_vector(seed=1)
        extractor = _make_extractor_with_fixed_embedding(emb)

        supporting_facts = [
            {
                'text': 'Metformin treats type 2 diabetes.',
                'distance': 0.1,
                'quality_score': 0.9,
                'evidence_grade': 'A',
                'confidence_modifier': 1.0,
            },
            {
                'text': 'Metformin is first-line therapy for T2DM.',
                'distance': 0.1,
                'quality_score': 0.9,
                'evidence_grade': 'A',
                'confidence_modifier': 1.0,
            },
        ]

        with mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim):
            label, score = extractor.calculate_confidence_score(
                'Metformin is first-line treatment for type 2 diabetes.',
                supporting_facts,
            )

        assert isinstance(score, float), f"Score must be float, got {type(score)}"
        assert label in ('HIGH', 'MEDIUM', 'LOW'), f"Invalid label: {label}"
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"
        # High-similarity + high-quality facts must produce HIGH confidence
        assert label == 'HIGH', (
            f"High-similarity grade-A facts must yield HIGH label, got {label} (score={score}). "
            f"Check CONFIDENCE_HIGH threshold in config."
        )

    def test_absent_supporting_facts_yield_low_label(self):
        """Empty supporting_facts list must short-circuit to label='LOW', score=0.1."""
        emb = _unit_vector(seed=2)
        extractor = _make_extractor_with_fixed_embedding(emb)

        supporting_facts = []  # no evidence at all

        with mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim):
            label, score = extractor.calculate_confidence_score(
                'Some unverified medical claim with no evidence.',
                supporting_facts,
            )

        assert isinstance(score, float), f"Score must be float, got {type(score)}"
        assert label in ('HIGH', 'MEDIUM', 'LOW'), f"Invalid label: {label}"
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"
        assert label == 'LOW', (
            f"Absent supporting facts must yield LOW label, got {label} (score={score})"
        )

    def test_orthogonal_facts_yield_low_or_medium(self):
        """Orthogonal claim/fact vectors + grade-D quality must NOT yield 'HIGH'.

        We give the extractor side_effect so the claim call returns claim_vec and
        each fact call returns a Gram-Schmidt-orthogonal fact_vec (cosine_sim ≈ 0).
        """
        claim_vec = _unit_vector(seed=10)

        # Build a vector orthogonal to claim_vec via Gram-Schmidt
        seed_vec = np.zeros(768, dtype=np.float32)
        seed_vec[0] = 1.0
        projected = seed_vec - np.dot(seed_vec, claim_vec) * claim_vec
        norm = np.linalg.norm(projected)
        fact_vec = (projected / norm) if norm > 1e-8 else seed_vec

        e = ClaimExtractor.__new__(ClaimExtractor)
        e.config = get_global_config()
        # First call is for claim text; subsequent calls are for each fact text
        e.get_sentence_embedding = mock.MagicMock(
            side_effect=[claim_vec, fact_vec, fact_vec]
        )

        supporting_facts = [
            {
                'text': 'Unrelated fact about cardiology procedures.',
                'distance': 0.9,
                'quality_score': 0.3,
                'evidence_grade': 'D',
                'confidence_modifier': 1.0,
            },
            {
                'text': 'Another unrelated fact about ophthalmology.',
                'distance': 0.9,
                'quality_score': 0.3,
                'evidence_grade': 'D',
                'confidence_modifier': 1.0,
            },
        ]

        with mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim):
            label, score = e.calculate_confidence_score(
                'A medical claim about diabetes with no supporting evidence.',
                supporting_facts,
            )

        assert isinstance(score, float), f"Score must be float, got {type(score)}"
        assert label in ('HIGH', 'MEDIUM', 'LOW'), f"Invalid label: {label}"
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"
        assert label != 'HIGH', (
            f"Orthogonal low-quality facts must NOT yield HIGH label, got {label} (score={score})"
        )

    def test_score_and_label_bounds_always_valid(self):
        """Sanity check: label is always in the valid set and score is always in [0.0, 1.0]
        regardless of mixed fact composition."""
        emb = _unit_vector(seed=3)
        extractor = _make_extractor_with_fixed_embedding(emb)

        # Mixed-quality facts
        supporting_facts = [
            {
                'text': 'Fact A with moderate quality evidence.',
                'distance': 0.5,
                'quality_score': 0.6,
                'evidence_grade': 'B',
                'confidence_modifier': 1.0,
            },
            {
                'text': 'Fact B with lower quality evidence.',
                'distance': 0.7,
                'quality_score': 0.4,
                'evidence_grade': 'C',
                'confidence_modifier': 1.0,
            },
        ]

        with mock.patch.object(claim_extractor_fixed, 'cosine_similarity', side_effect=_np_cosine_sim):
            label, score = extractor.calculate_confidence_score(
                'A medical claim with mixed supporting evidence.',
                supporting_facts,
            )

        assert isinstance(score, float), f"Score must be float, got {type(score)}"
        assert label in ('HIGH', 'MEDIUM', 'LOW'), f"Invalid label: {label}"
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"
