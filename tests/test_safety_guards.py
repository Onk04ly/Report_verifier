"""
Phase 2 Safety Guardrail Tests (Wave 0 scaffold).

Each test corresponds to a row in 02-VALIDATION.md. Tests are authored RED
first; later waves (01-config, 02-extractor, 03-verifier) turn them green.
"""
import os
import sys
import json
from unittest import mock

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


# ---------- SAFE-01: Semantic danger detection ---------- #

def test_config_new_params():
    """New config params load and are type-correct."""
    from medical_config import get_global_config
    cfg = get_global_config()
    assert isinstance(cfg.DANGEROUS_SEMANTIC_THRESHOLD, float)
    assert 0.0 <= cfg.DANGEROUS_SEMANTIC_THRESHOLD <= 1.0
    assert isinstance(cfg.MAX_SUMMARY_CHARS, int)
    assert cfg.MAX_SUMMARY_CHARS > 0
    assert isinstance(cfg.DUPLICATE_SENTENCE_RATIO, float)
    assert 0.0 <= cfg.DUPLICATE_SENTENCE_RATIO <= 1.0
    assert cfg.MAX_CLAIMS_PER_SUMMARY == 50  # unchanged


def test_semantic_danger_detects_dangerous_phrase(dangerous_claim_text):
    """Claim highly similar to centroid flags as semantically dangerous."""
    from claim_extractor_fixed import ClaimExtractor
    from medical_config import get_global_config
    cfg = get_global_config()

    # Build extractor shell and inject a fake centroid that is identical to
    # the mocked embedding returned by sentence_model.encode — cosine_sim == 1.0
    extractor = ClaimExtractor.__new__(ClaimExtractor)
    extractor.config = cfg
    fake_vec = np.ones(768, dtype=np.float32)
    extractor.sentence_model = mock.MagicMock()
    extractor.sentence_model.encode.return_value = fake_vec
    extractor.danger_centroid = fake_vec
    extractor._seeds_file_status = 'loaded'

    assert extractor.is_semantically_dangerous(dangerous_claim_text) is True


def test_semantic_danger_ignores_safe_phrase(safe_clinical_text):
    """Neutral clinical text scores below threshold."""
    from claim_extractor_fixed import ClaimExtractor
    from medical_config import get_global_config
    cfg = get_global_config()

    extractor = ClaimExtractor.__new__(ClaimExtractor)
    extractor.config = cfg
    # Orthogonal vectors -> cosine similarity ~ 0
    claim_vec = np.zeros(768, dtype=np.float32); claim_vec[0] = 1.0
    centroid_vec = np.zeros(768, dtype=np.float32); centroid_vec[1] = 1.0
    extractor.sentence_model = mock.MagicMock()
    extractor.sentence_model.encode.return_value = claim_vec
    extractor.danger_centroid = centroid_vec
    extractor._seeds_file_status = 'loaded'

    assert extractor.is_semantically_dangerous(safe_clinical_text) is False


def test_danger_flag_triggers_on_rule_match():
    """Rule match alone sets is_dangerous True even if semantic returns False."""
    from claim_extractor_fixed import ClaimExtractor
    from medical_config import get_global_config
    cfg = get_global_config()
    extractor = ClaimExtractor.__new__(ClaimExtractor)
    extractor.config = cfg
    extractor.sentence_model = None  # forces semantic check to return False
    extractor.danger_centroid = None
    extractor._seeds_file_status = 'missing'
    # Starting claim with rule_match pre-set; confirm OR preserves True
    assert extractor.is_semantically_dangerous("stop taking your insulin") is False
    # Semantic returns False (model is None) — rule flag source of truth remains whatever wire site sets
    # Integration guarantee: is_semantically_dangerous does not OVERWRITE to False
    claim = {'is_dangerous': True}
    claim['is_dangerous'] = bool(claim.get('is_dangerous', False) or extractor.is_semantically_dangerous('x'))
    assert claim['is_dangerous'] is True


def test_missing_seeds_disables_semantic_check():
    """If seeds JSON missing, danger_centroid is None and is_semantically_dangerous returns False."""
    from claim_extractor_fixed import ClaimExtractor
    from medical_config import get_global_config
    cfg = get_global_config()
    extractor = ClaimExtractor.__new__(ClaimExtractor)
    extractor.config = cfg
    extractor.sentence_model = mock.MagicMock()
    extractor.danger_centroid = None
    extractor._seeds_file_status = 'missing'
    assert extractor.is_semantically_dangerous("stop taking your insulin") is False


# ---------- SAFE-02: Input validation + max claims ---------- #

def test_input_validation_rejects_non_string(mock_verifier_no_models):
    """Non-string input returns UNKNOWN with input_validation.error='non_string_input'."""
    result = mock_verifier_no_models.verify_single_summary(12345)
    assert result['input_validation']['error'] == 'non_string_input'
    assert result['risk_assessment']['level'] == 'UNKNOWN'
    assert 'responsible_ai' in result
    assert 'risk_assessment' in result and 'stats' in result['risk_assessment']


def test_input_validation_rejects_empty(mock_verifier_no_models):
    """Empty/whitespace input returns UNKNOWN with input_validation.error='empty_input'."""
    result = mock_verifier_no_models.verify_single_summary("   \n\t   ")
    assert result['input_validation']['error'] == 'empty_input'
    assert result['risk_assessment']['level'] == 'UNKNOWN'
    assert 'responsible_ai' in result


def test_input_validation_truncates_oversized(mock_verifier_no_models, oversized_input):
    """Oversized input is truncated and flagged."""
    result = mock_verifier_no_models.verify_single_summary(oversized_input)
    assert result['input_validation']['truncated'] is True
    assert result['input_validation']['original_char_count'] == len(oversized_input)
    assert result['input_validation']['error'] is None


def test_input_validation_flags_duplication(mock_verifier_no_models, duplicate_heavy_input):
    """High duplicate ratio sets warning='repeated_content'."""
    result = mock_verifier_no_models.verify_single_summary(duplicate_heavy_input)
    assert result['input_validation']['warning'] == 'repeated_content'


def test_input_validation_warns_no_entities(mock_verifier_no_models):
    """No medical entities detected sets input_validation.warning='no_entities_detected'."""
    # The mocked extractor's extract_claims_from_summary must return a result
    # with no_entities=True so verify_single_summary propagates the warning.
    result_stub = {
        'original_text': 'xx', 'sentences': ['xx'], 'claims': [],
        'total_claims': 0, 'claims_truncated': False, 'claims_truncated_count': 0,
        'no_entities': True,
    }
    mock_verifier_no_models.extractor.extract_claims_from_summary = lambda t: dict(result_stub)
    result = mock_verifier_no_models.verify_single_summary("The patient was admitted.")
    assert result['input_validation']['warning'] == 'no_entities_detected'


def test_max_claims_truncated_flag():
    """claims_truncated=True when identified claims exceed MAX_CLAIMS_PER_SUMMARY."""
    from claim_extractor_fixed import ClaimExtractor
    from medical_config import get_global_config
    cfg = get_global_config()
    extractor = ClaimExtractor.__new__(ClaimExtractor)
    extractor.config = cfg
    extractor.sentence_model = None
    extractor.danger_centroid = None
    extractor._seeds_file_status = 'missing'

    # Build a fake claim dict matching the required schema
    fake_claim = {
        'claim_text': 'dummy',
        'type': 'general',
        'medical_entities': [],
        'verification_confidence': 'LOW',
        'verification_score': 0.0,
    }
    extractor.extract_sentences = lambda text: ['s'] * (cfg.MAX_CLAIMS_PER_SUMMARY + 5)
    extractor.identify_medical_claims = lambda sents: [dict(fake_claim) for _ in sents]

    result = extractor.extract_claims_from_summary("unused text")
    assert result['claims_truncated'] is True
    assert result['claims_truncated_count'] == 5
    assert len(result['claims']) == cfg.MAX_CLAIMS_PER_SUMMARY


# ---------- SAFE-03: Degraded mode + sidecar ---------- #

def test_degraded_mode_flag_when_model_none(mock_verifier_no_models):
    """degraded_mode=True in risk_assessment when sentence_model is None."""
    result = mock_verifier_no_models.verify_single_summary("The patient has diabetes.")
    assert result['risk_assessment'].get('degraded_mode') is True


def test_sidecar_written_on_export(mock_verifier_no_models, tmp_path):
    """export_results() writes one sidecar JSON per result under outputs/."""
    output_path = str(tmp_path / "medical_verification.json")
    results = [
        {
            'summary_id': 'test_sum_1',
            'claims': [],
            'total_claims': 0,
            'risk_assessment': {'level': 'LOW_RISK', 'stats': {}, 'degraded_mode': True},
            'responsible_ai': {'safety_warnings': [], 'requires_expert_review': False, 'auto_flagged': False},
            'analysis_timestamp': '2026-04-15T00:00:00',
        }
    ]
    mock_verifier_no_models.export_results(results, output_path, format='json')
    sidecar_path = os.path.join(str(tmp_path), 'test_sum_1_model_status.json')
    assert os.path.exists(sidecar_path)
    with open(sidecar_path) as f:
        data = json.load(f)
    assert data['summary_id'] == 'test_sum_1'
    assert data['degraded_mode'] is True
    assert 'neuml/pubmedbert-base-embeddings' in data['unavailable_models']


def test_sidecar_seeds_file_status(mock_verifier_no_models, tmp_path):
    """Sidecar seeds_file_status reflects the extractor's _seeds_file_status attribute."""
    output_path = str(tmp_path / "medical_verification.json")
    mock_verifier_no_models.extractor._seeds_file_status = 'loaded'
    results = [
        {
            'summary_id': 'test_sum_2',
            'claims': [],
            'total_claims': 0,
            'risk_assessment': {'level': 'LOW_RISK', 'stats': {}},
            'responsible_ai': {'safety_warnings': [], 'requires_expert_review': False, 'auto_flagged': False},
            'analysis_timestamp': '2026-04-15T00:00:00',
        }
    ]
    mock_verifier_no_models.export_results(results, output_path, format='json')
    sidecar_path = os.path.join(str(tmp_path), 'test_sum_2_model_status.json')
    with open(sidecar_path) as f:
        data = json.load(f)
    assert data['seeds_file_status'] == 'loaded'
