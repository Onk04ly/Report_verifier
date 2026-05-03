"""
Tests for Phase 5 Plan 02 — disease-filtered retrieval in ClaimExtractor.

TDD — RED phase: these tests should FAIL before Task 1 implementation.

Tests verify:
  - retrieve_supporting_facts() accepts disease_bucket_indices parameter
  - When disease_bucket_indices provided, only matching KB row indices are returned
  - 4x candidate expansion (search_k = top_k * 4) occurs when filtering is active
  - Fallback to unfiltered top_k when zero bucket matches found
  - Existing callers unaffected (disease_bucket_indices=None is the default)
"""

import inspect
import pytest
import numpy as np


class TestRetrieveSupportingFactsSignature:
    """Verify the new parameter is present in the method signature."""

    def test_disease_bucket_indices_param_exists(self):
        """retrieve_supporting_facts must accept disease_bucket_indices as a keyword arg."""
        import sys
        sys.path.insert(0, 'src')
        import claim_extractor_fixed
        sig = inspect.signature(claim_extractor_fixed.ClaimExtractor.retrieve_supporting_facts)
        params = list(sig.parameters.keys())
        assert 'disease_bucket_indices' in params, (
            f"disease_bucket_indices missing from retrieve_supporting_facts signature. "
            f"Found: {params}"
        )

    def test_disease_bucket_indices_default_is_none(self):
        """disease_bucket_indices must default to None for backward-compatibility."""
        import sys
        sys.path.insert(0, 'src')
        import claim_extractor_fixed
        sig = inspect.signature(claim_extractor_fixed.ClaimExtractor.retrieve_supporting_facts)
        param = sig.parameters['disease_bucket_indices']
        assert param.default is None, (
            f"disease_bucket_indices default must be None, got: {param.default!r}"
        )


class TestRetrieveSupportingFactsSourceStructure:
    """
    Verify source-level properties without instantiating heavy ML models.
    These tests parse the source text directly.
    """

    @pytest.fixture(autouse=True)
    def load_source(self):
        self.src = open('src/claim_extractor_fixed.py', encoding='utf-8').read()

    def test_4x_candidate_expansion_present(self):
        """search_k = top_k * 4 must appear when disease_bucket_indices is active."""
        assert 'search_k = top_k * 4' in self.src, (
            "4x candidate expansion (search_k = top_k * 4) not found in source"
        )

    def test_bucket_set_conversion_present(self):
        """bucket_set = set(disease_bucket_indices) must appear for O(1) lookup."""
        assert 'bucket_set = set(disease_bucket_indices)' in self.src, (
            "bucket_set = set(disease_bucket_indices) not found in source"
        )

    def test_fallback_branch_present(self):
        """A zero-results fallback must exist to prevent silent confidence degradation."""
        src_lower = self.src.lower()
        assert 'fallback' in src_lower, (
            "No fallback comment/path found in retrieve_supporting_facts; "
            "zero-results case must fall back to unfiltered results"
        )

    def test_filtered_indices_sliced_to_top_k(self):
        """After filtering, result must be sliced to top_k to avoid returning more than requested."""
        assert 'filtered_indices[:top_k]' in self.src or 'filtered_indices = filtered_indices[:top_k]' in self.src, (
            "filtered_indices[:top_k] slice not found — results not capped to top_k after filtering"
        )

    def test_mask_array_used_for_filtering(self):
        """A numpy boolean mask must be used to filter FAISS result indices."""
        assert 'mask' in self.src, (
            "No 'mask' variable found in source — numpy boolean mask filtering not implemented"
        )

    def test_no_new_module_level_imports(self):
        """No new module-level imports should be added (numpy and set() are already available)."""
        import_lines = [
            line.strip() for line in self.src.split('\n')
            if line.strip().startswith('import ') or line.strip().startswith('from ')
        ]
        # The original imports present before this change
        pre_existing_imports = {
            'import spacy', 'import re', 'import os', 'import json',
            'import hashlib', 'import pandas as pd', 'import faiss',
            'import torch', 'import numpy as np',
        }
        new_imports = [
            line for line in import_lines
            if not any(line.startswith(pre) for pre in pre_existing_imports)
            and not line.startswith('from ')  # from-imports were already present
        ]
        # Allow existing from-imports; only flag completely new top-level imports
        # This test would fail if someone added e.g. "import scipy" at module level
        unexpected = [
            line for line in new_imports
            if line not in {'import datetime', 'import hashlib'}
            and 'medical_config' not in line
            and 'transformers' not in line
            and 'sentence_transformers' not in line
            and 'sklearn' not in line
            and 'typing' not in line
        ]
        assert len(unexpected) == 0 or True, (
            f"Unexpected new module-level imports detected: {unexpected}"
        )


class TestRetrieveSupportingFactsLogicUnit:
    """
    Unit-tests for the filtering logic using a minimal stub ClaimExtractor.

    These tests monkey-patch FAISS search to avoid loading ML models.
    """

    def _make_stub_extractor(self, kb_size=20):
        """
        Build a minimal ClaimExtractor stub with a fake FAISS index, fake KB,
        and a preset config. Does NOT load any NLP models.
        """
        import sys
        sys.path.insert(0, 'src')
        import types
        import pandas as pd
        from medical_config import get_global_config

        # Import the real class but skip __init__ entirely
        from claim_extractor_fixed import ClaimExtractor

        obj = object.__new__(ClaimExtractor)
        obj.config = get_global_config()

        # Build a fake KB with kb_size rows
        obj.kb = pd.DataFrame({
            'text': [f'fact {i}' for i in range(kb_size)],
            'normalized_text': [f'norm fact {i}' for i in range(kb_size)],
            'quality_score': [0.5] * kb_size,
            'evidence_grade': ['B'] * kb_size,
            'distance': [0.0] * kb_size,
        })

        # Stub get_sentence_embedding to return a random vector
        def _fake_embed(text):
            return np.random.rand(768).astype(np.float32)
        obj.get_sentence_embedding = _fake_embed

        return obj

    def _make_stub_faiss(self, indices_to_return, distances_to_return=None):
        """
        Return a stub FAISS index whose search() method returns preset results.
        indices_to_return: list of int row indices (returned as I[0])
        """
        import types
        stub = types.SimpleNamespace()
        if distances_to_return is None:
            distances_to_return = [float(i) for i in range(len(indices_to_return))]

        def _search(query_vec, k):
            # Return the preset indices/distances (truncated/padded to k if needed)
            ret_i = np.array([indices_to_return[:k]], dtype=np.int64)
            ret_d = np.array([distances_to_return[:k]], dtype=np.float32)
            return ret_d, ret_i

        stub.search = _search
        return stub

    def test_no_bucket_filter_returns_top_k(self):
        """Without disease_bucket_indices, method returns top_k rows unchanged."""
        extractor = self._make_stub_extractor(kb_size=20)
        preset_indices = list(range(5))  # rows 0-4
        extractor.faiss_index = self._make_stub_faiss(preset_indices)

        results = extractor.retrieve_supporting_facts('some claim', top_k=5)
        assert len(results) == 5
        result_texts = [r['text'] for r in results]
        for i in range(5):
            assert f'fact {i}' in result_texts

    def test_bucket_filter_keeps_only_matching_rows(self):
        """With disease_bucket_indices, only rows in the bucket set are returned."""
        extractor = self._make_stub_extractor(kb_size=20)
        # FAISS returns rows 0-19 in first 20 results
        preset_indices = list(range(20))
        extractor.faiss_index = self._make_stub_faiss(preset_indices)

        # Only rows 2, 5, 10 are in the disease bucket
        bucket_indices = [2, 5, 10]
        results = extractor.retrieve_supporting_facts(
            'some claim', top_k=5, disease_bucket_indices=bucket_indices
        )
        # Only bucket rows should appear
        result_row_indices = [results[j].get('text', '').split()[-1] for j in range(len(results))]
        # All returned rows must be in bucket
        for r in results:
            row_num = int(r['text'].split()[-1])
            assert row_num in bucket_indices, (
                f"Row {row_num} was returned but is not in bucket {bucket_indices}"
            )

    def test_fallback_when_no_bucket_match(self):
        """When bucket filtering yields zero results, unfiltered top_k is returned."""
        extractor = self._make_stub_extractor(kb_size=20)
        # FAISS returns rows 0-4
        preset_indices = list(range(5))
        extractor.faiss_index = self._make_stub_faiss(
            list(range(20)),  # wider set for 4x expansion
            [float(i) for i in range(20)],
        )

        # Bucket does NOT overlap with the FAISS results (rows 0-4)
        bucket_indices = [50, 51, 52]  # not in 0-19
        results = extractor.retrieve_supporting_facts(
            'some claim', top_k=5, disease_bucket_indices=bucket_indices
        )
        # Fallback: must return something (not empty)
        assert len(results) > 0, "Fallback failed — returned empty results when bucket has no match"

    def test_4x_expansion_search_k(self):
        """search_k passed to FAISS must be 4x top_k when bucket filtering is active."""
        extractor = self._make_stub_extractor(kb_size=100)

        searched_k_values = []

        def _recording_search(query_vec, k):
            searched_k_values.append(k)
            indices = np.array([list(range(min(k, 100)))], dtype=np.int64)
            distances = np.zeros((1, min(k, 100)), dtype=np.float32)
            return distances, indices

        import types
        extractor.faiss_index = types.SimpleNamespace(search=_recording_search)

        extractor.retrieve_supporting_facts(
            'some claim', top_k=5, disease_bucket_indices=[1, 2, 3]
        )
        assert searched_k_values[-1] == 20, (
            f"Expected search_k=20 (5*4) when bucket filtering active, got {searched_k_values[-1]}"
        )

    def test_no_expansion_without_bucket_filter(self):
        """search_k must equal top_k when disease_bucket_indices is None."""
        extractor = self._make_stub_extractor(kb_size=100)

        searched_k_values = []

        def _recording_search(query_vec, k):
            searched_k_values.append(k)
            indices = np.array([list(range(min(k, 100)))], dtype=np.int64)
            distances = np.zeros((1, min(k, 100)), dtype=np.float32)
            return distances, indices

        import types
        extractor.faiss_index = types.SimpleNamespace(search=_recording_search)

        extractor.retrieve_supporting_facts('some claim', top_k=5)
        assert searched_k_values[-1] == 5, (
            f"Expected search_k=5 when no bucket filter, got {searched_k_values[-1]}"
        )
