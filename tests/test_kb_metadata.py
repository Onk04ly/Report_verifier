"""
TDD tests for _write_kb_metadata() in MedicalPreprocessor.

RED phase: these tests define expected behavior before implementation.
"""

import hashlib
import json
import os
import sys
import tempfile
import types
import unittest.mock as mock

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Stub heavy dependencies so the import of medical_preprocessor doesn't
# attempt to load spacy, faiss, torch, etc.
# ---------------------------------------------------------------------------

_HEAVY = [
    'spacy', 'faiss', 'torch', 'transformers',
    'sentence_transformers',
    'sklearn', 'sklearn.feature_extraction', 'sklearn.feature_extraction.text',
    'sklearn.metrics', 'sklearn.metrics.pairwise',
]

for _mod in _HEAVY:
    if _mod not in sys.modules:
        sys.modules[_mod] = mock.MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from medical_preprocessor import MedicalPreprocessor  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_preprocessor(primary_method: str = 'pubmedbert') -> MedicalPreprocessor:
    mp = MedicalPreprocessor.__new__(MedicalPreprocessor)
    mp.available_methods = [primary_method]
    mp.embedding_models = {}
    return mp


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWriteKbMetadata:
    """Tests for MedicalPreprocessor._write_kb_metadata()."""

    def test_method_exists(self):
        """_write_kb_metadata must exist on MedicalPreprocessor."""
        mp = _make_preprocessor()
        assert hasattr(mp, '_write_kb_metadata'), \
            "_write_kb_metadata not found on MedicalPreprocessor"
        assert callable(mp._write_kb_metadata)

    def test_all_six_fields_present(self, tmp_path):
        """Metadata JSON must contain all six required fields."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'col1,col2\nval1,val2\n')
        np.save(str(npy_path), np.array([1.0, 2.0]))

        df = pd.DataFrame({'query_original': ['query_a', 'query_b']})
        mp = _make_preprocessor('pubmedbert')
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path, 'r', encoding='utf-8') as fh:
            meta = json.load(fh)

        required = {
            'generated_at', 'embedding_model', 'row_count',
            'csv_sha256', 'embeddings_sha256', 'pubmed_queries',
        }
        missing = required - set(meta.keys())
        assert not missing, f"Missing metadata fields: {missing}"

    def test_csv_sha256_matches_file(self, tmp_path):
        """csv_sha256 must equal the SHA-256 of the CSV file bytes."""
        csv_data = b'col1,col2\nval1,val2\n'
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(csv_data)
        np.save(str(npy_path), np.array([1.0]))

        df = pd.DataFrame({'query_original': ['q1']})
        mp = _make_preprocessor()
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['csv_sha256'] == _sha256_bytes(csv_data)

    def test_embeddings_sha256_matches_file(self, tmp_path):
        """embeddings_sha256 must equal the SHA-256 of the .npy file bytes."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'a,b\n1,2\n')
        arr_data = np.array([0.1, 0.2, 0.3])
        np.save(str(npy_path), arr_data)

        npy_bytes = npy_path.read_bytes()
        df = pd.DataFrame({'query_original': ['q1']})
        mp = _make_preprocessor()
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['embeddings_sha256'] == _sha256_bytes(npy_bytes)

    def test_row_count_is_len_of_df(self, tmp_path):
        """row_count must equal len(final_df)."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n2\n3\n')
        np.save(str(npy_path), np.zeros(3))

        df = pd.DataFrame({'query_original': ['q'] * 5})
        mp = _make_preprocessor()
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['row_count'] == 5

    def test_pubmed_queries_counts_unique(self, tmp_path):
        """pubmed_queries must be the count of unique query_original values."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n')
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['a', 'b', 'a', 'c']})
        mp = _make_preprocessor()
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['pubmed_queries'] == 3  # unique: a, b, c

    def test_pubmed_queries_zero_when_column_absent(self, tmp_path):
        """pubmed_queries must be 0 when query_original column is absent."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n')
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'other_col': ['x']})
        mp = _make_preprocessor()
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['pubmed_queries'] == 0

    def test_embedding_model_pubmedbert(self, tmp_path):
        """Primary method 'pubmedbert' maps to 'neuml/pubmedbert-base-embeddings'."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n')
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor('pubmedbert')
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['embedding_model'] == 'neuml/pubmedbert-base-embeddings'

    def test_embedding_model_spubmedbert(self, tmp_path):
        """Primary method 'spubmedbert' maps to 'pritamdeka/S-PubMedBert-MS-MARCO'."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n')
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor('spubmedbert')
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['embedding_model'] == 'pritamdeka/S-PubMedBert-MS-MARCO'

    def test_embedding_model_tfidf(self, tmp_path):
        """Primary method 'tfidf' maps to 'tfidf'."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n')
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor('tfidf')
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert meta['embedding_model'] == 'tfidf'

    def test_raises_file_not_found_if_csv_missing(self, tmp_path):
        """FileNotFoundError must be raised if CSV artifact does not exist."""
        npy_path = tmp_path / 'test.npy'
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor()

        with pytest.raises(FileNotFoundError):
            mp._write_kb_metadata(str(tmp_path / 'missing.csv'), str(npy_path), df)

    def test_raises_file_not_found_if_npy_missing(self, tmp_path):
        """FileNotFoundError must be raised if .npy artifact does not exist."""
        csv_path = tmp_path / 'test.csv'
        csv_path.write_bytes(b'c\n1\n')

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor()

        with pytest.raises(FileNotFoundError):
            mp._write_kb_metadata(str(csv_path), str(tmp_path / 'missing.npy'), df)

    def test_no_partial_json_on_missing_csv(self, tmp_path):
        """No JSON file must be written when CSV artifact is missing."""
        npy_path = tmp_path / 'test.npy'
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor()

        with pytest.raises(FileNotFoundError):
            mp._write_kb_metadata(str(tmp_path / 'missing.csv'), str(npy_path), df)

        # No kb_metadata.json should have been written
        meta_path = tmp_path / 'kb_metadata.json'
        assert not meta_path.exists(), \
            "Partial kb_metadata.json was written despite missing CSV"

    def test_return_value_is_path_to_metadata_json(self, tmp_path):
        """Return value must be the path to kb_metadata.json."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n')
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor()
        result = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        assert result.endswith('kb_metadata.json')
        assert os.path.exists(result)

    def test_generated_at_is_utc_iso8601(self, tmp_path):
        """generated_at must be a UTC ISO-8601 timestamp ending with 'Z'."""
        csv_path = tmp_path / 'test.csv'
        npy_path = tmp_path / 'test.npy'
        csv_path.write_bytes(b'c\n1\n')
        np.save(str(npy_path), np.zeros(1))

        df = pd.DataFrame({'query_original': ['q']})
        mp = _make_preprocessor()
        result_path = mp._write_kb_metadata(str(csv_path), str(npy_path), df)

        with open(result_path) as fh:
            meta = json.load(fh)

        assert isinstance(meta['generated_at'], str)
        assert meta['generated_at'].endswith('Z'), \
            f"generated_at should end with 'Z', got: {meta['generated_at']}"

    def test_preprocess_knowledge_base_calls_write_metadata(self):
        """preprocess_knowledge_base() must call _write_kb_metadata as its last step."""
        import inspect
        src = inspect.getsource(MedicalPreprocessor.preprocess_knowledge_base)
        assert '_write_kb_metadata' in src, \
            "_write_kb_metadata not called from preprocess_knowledge_base()"
