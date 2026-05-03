"""
Disease KB Buckets
==================

Computes per-disease knowledge-base article buckets and centroid vectors
used by Phase 5 disease-scope specialization.

This module is intentionally lightweight: it depends only on numpy, pandas,
and medical_config. It does NOT import ClaimExtractor or faiss.

Usage (CLI):
    python src/disease_buckets.py

Usage (API):
    from src.disease_buckets import build_disease_buckets, save_disease_buckets, load_disease_buckets
    buckets = build_disease_buckets(
        'data/expanded_knowledge_base_preprocessed.csv',
        'data/kb_embeddings_preprocessed.npy',
    )
    save_disease_buckets(buckets, 'data/disease_centroids.npz')
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any

import numpy as np
import pandas as pd

from medical_config import get_global_config


# --------------------------------------------------------------------------- #
# Disease keyword maps (module-level constants)
# Exact strings must match 'category' column values in the KB CSV.
# --------------------------------------------------------------------------- #

DISEASE_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "type1_diabetes": [
        "diabetes_mellitus_management",
        "insulin_diabetes",
        "diabetic_nephropathy",
        "diabetic_retinopathy",
        "gestational_diabetes",
    ],
    "metastatic_cancer": [
        "chemotherapy_cancer",
        "immunotherapy_cancer",
        "targeted_therapy_oncology",
        "palliative_care_cancer",
        "lung_cancer_treatment",
        "breast_cancer_chemotherapy",
        "pancreatic_cancer_treatment",
        "surgical_oncology",
        "radiation_therapy_cancer",
        "ovarian_cancer_therapy",
        "colorectal_cancer_therapy",
        "lymphoma_chemotherapy",
        "bladder_cancer_therapy",
        "prostate_cancer_treatment",
        "skin_cancer_treatment",
        "brain_tumor_treatment",
        "pediatric_cancer_treatment",
    ],
}


# --------------------------------------------------------------------------- #
# DiseaseKBBuckets dataclass
# --------------------------------------------------------------------------- #

@dataclass
class DiseaseKBBuckets:
    """
    Container for per-disease KB article buckets and centroid vectors.

    Attributes:
        centroids: dict mapping disease_slug -> centroid vector of shape (768,)
        article_indices: dict mapping disease_slug -> list of KB row indices
        config_snapshot: snapshot of disease config at build time
    """

    centroids: Dict[str, np.ndarray]       # disease_slug -> centroid vector (768,)
    article_indices: Dict[str, List[int]]  # disease_slug -> list of KB row indices
    config_snapshot: Dict[str, Any]        # snapshot of disease config at build time


# --------------------------------------------------------------------------- #
# build_disease_buckets
# --------------------------------------------------------------------------- #

def build_disease_buckets(
    kb_csv_path: str,
    embeddings_path: str,
    config=None,
) -> DiseaseKBBuckets:
    """
    Build per-disease KB article buckets and centroid vectors.

    Algorithm (per D-04 and D-05):
    - Step A: Load KB CSV (category + quality_score columns) and embedding matrix.
    - Step B: For each disease slug, select top-K highest-quality candidate articles
              and compute a normalized centroid vector.
    - Step C: Assign all KB articles to disease buckets where cosine similarity
              to the centroid meets the threshold.
    - Step D: Resolve overlapping assignments by keeping each article only in the
              bucket with the highest cosine similarity.

    Args:
        kb_csv_path: Path to expanded_knowledge_base_preprocessed.csv.
        embeddings_path: Path to kb_embeddings_preprocessed.npy.
        config: Optional ConfigurationSettings instance; defaults to global config.

    Returns:
        DiseaseKBBuckets with centroids, article_indices, and config_snapshot.

    Raises:
        ValueError: If no candidate articles are found for any disease slug.
        FileNotFoundError: If kb_csv_path or embeddings_path do not exist.
    """
    cfg = config or get_global_config()
    dc = cfg.get_disease_config()

    # ---------------------------------------------------------------------- #
    # Step A — Load data
    # ---------------------------------------------------------------------- #
    if not os.path.exists(kb_csv_path):
        raise FileNotFoundError(f"KB CSV not found: {kb_csv_path}")
    if not os.path.exists(embeddings_path):
        raise FileNotFoundError(f"Embeddings file not found: {embeddings_path}")

    kb = pd.read_csv(kb_csv_path, usecols=["category", "quality_score"])
    embeddings = np.load(embeddings_path, mmap_mode="r").astype(np.float32)

    # Normalize all embeddings once — cosine sim = dot product on unit vectors
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    norm_embeddings = embeddings / norms  # shape (N, 768)

    # ---------------------------------------------------------------------- #
    # Step B — Compute centroids per disease
    # ---------------------------------------------------------------------- #
    centroids: Dict[str, np.ndarray] = {}
    all_sims: Dict[str, np.ndarray] = {}  # cached for Step C / D

    for disease in dc["disease_list"]:
        if disease not in DISEASE_CATEGORY_KEYWORDS:
            raise ValueError(
                f"Disease slug '{disease}' has no entry in DISEASE_CATEGORY_KEYWORDS"
            )

        keywords = DISEASE_CATEGORY_KEYWORDS[disease]
        candidate_mask = kb["category"].isin(keywords)
        candidate_indices = np.where(candidate_mask)[0]

        if len(candidate_indices) == 0:
            raise ValueError(
                f"No KB articles found for disease '{disease}' "
                f"(searched categories: {keywords})"
            )

        candidate_quality = kb["quality_score"].iloc[candidate_indices].values
        top_k = dc["centroid_top_k"]
        # argsort ascending, take last top_k (highest quality)
        top_k_local = np.argsort(candidate_quality)[::-1][:top_k]
        top_k_indices = candidate_indices[top_k_local]

        centroid = norm_embeddings[top_k_indices].mean(axis=0)
        centroid_norm = np.linalg.norm(centroid)
        centroid /= (centroid_norm if centroid_norm > 0 else 1.0)  # re-normalize
        centroids[disease] = centroid

        # Precompute cosine similarities for all KB articles (Step C / D)
        all_sims[disease] = norm_embeddings @ centroid  # shape (N,)

    # ---------------------------------------------------------------------- #
    # Step C — Assign all KB articles to disease buckets
    # ---------------------------------------------------------------------- #
    threshold = dc["centroid_sim_threshold"]
    article_indices: Dict[str, List[int]] = {}

    for disease in dc["disease_list"]:
        sim = all_sims[disease]
        bucket = np.where(sim >= threshold)[0].tolist()
        article_indices[disease] = bucket

    # ---------------------------------------------------------------------- #
    # Step D — Resolve overlaps (D-05: assign to highest cosine sim)
    # ---------------------------------------------------------------------- #
    diseases = dc["disease_list"]
    if len(diseases) >= 2:
        # Build overlap sets between all pairs and resolve
        # For the 2-disease case this is simple; generalises to N diseases via
        # repeated pairwise elimination.
        for i in range(len(diseases)):
            for j in range(i + 1, len(diseases)):
                d_i, d_j = diseases[i], diseases[j]
                set_i = set(article_indices[d_i])
                set_j = set(article_indices[d_j])
                overlaps = set_i & set_j

                to_remove_i: List[int] = []
                to_remove_j: List[int] = []

                for idx in overlaps:
                    sim_i = float(all_sims[d_i][idx])
                    sim_j = float(all_sims[d_j][idx])
                    if sim_i >= sim_j:
                        to_remove_j.append(idx)
                    else:
                        to_remove_i.append(idx)

                if to_remove_i:
                    remove_set_i = set(to_remove_i)
                    article_indices[d_i] = [
                        x for x in article_indices[d_i] if x not in remove_set_i
                    ]
                if to_remove_j:
                    remove_set_j = set(to_remove_j)
                    article_indices[d_j] = [
                        x for x in article_indices[d_j] if x not in remove_set_j
                    ]

    return DiseaseKBBuckets(
        centroids=centroids,
        article_indices=article_indices,
        config_snapshot=dc,
    )


# --------------------------------------------------------------------------- #
# save_disease_buckets
# --------------------------------------------------------------------------- #

def save_disease_buckets(buckets: DiseaseKBBuckets, output_path: str) -> None:
    """
    Save disease centroids and article indices to a .npz file.

    Centroid arrays are stored under their disease slug key.
    Article index arrays are stored under '{slug}_indices' keys.

    Args:
        buckets: DiseaseKBBuckets produced by build_disease_buckets().
        output_path: Destination path for the .npz file.
    """
    arrays: Dict[str, np.ndarray] = {}
    for slug, vec in buckets.centroids.items():
        arrays[slug] = vec
    for slug, idxs in buckets.article_indices.items():
        arrays[f"{slug}_indices"] = np.array(idxs, dtype=np.int64)
    np.savez(output_path, **arrays)


# --------------------------------------------------------------------------- #
# load_disease_buckets
# --------------------------------------------------------------------------- #

def load_disease_buckets(npz_path: str) -> DiseaseKBBuckets:
    """
    Load disease centroids and article indices from a previously saved .npz file.

    Args:
        npz_path: Path to the .npz file produced by save_disease_buckets().

    Returns:
        DiseaseKBBuckets with centroids and article_indices reconstructed.
        config_snapshot will be an empty dict (not persisted in .npz).
    """
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Disease buckets file not found: {npz_path}")

    data = np.load(npz_path)
    centroids: Dict[str, np.ndarray] = {}
    article_indices: Dict[str, List[int]] = {}

    for key in data.files:
        if key.endswith("_indices"):
            slug = key[: -len("_indices")]
            article_indices[slug] = data[key].tolist()
        else:
            centroids[key] = data[key]

    return DiseaseKBBuckets(
        centroids=centroids,
        article_indices=article_indices,
        config_snapshot={},
    )


# --------------------------------------------------------------------------- #
# CLI entrypoint
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys

    # Resolve paths relative to the repository root (one level up from src/).
    # When running inside a git worktree, data/ lives in the main repo tree;
    # walk up until we find a directory that contains data/.
    _src_dir = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_src_dir)

    # When running inside a git worktree, the worktree may have a data/ dir
    # but it only contains git-tracked files (small). Large pre-computed
    # artifacts live in the main repository checkout. Resolve via git common dir.
    _kb_csv_check = os.path.join(_repo_root, "data", "expanded_knowledge_base_preprocessed.csv")
    if not os.path.isfile(_kb_csv_check):
        import subprocess  # noqa: PLC0415
        try:
            _git_common = subprocess.check_output(
                ["git", "rev-parse", "--git-common-dir"],
                cwd=_src_dir,
                text=True,
            ).strip()
            # common dir is .git (main) or .git/worktrees/<name> (worktree)
            _candidate = os.path.dirname(os.path.abspath(_git_common))
            _candidate_csv = os.path.join(_candidate, "data", "expanded_knowledge_base_preprocessed.csv")
            if os.path.isfile(_candidate_csv):
                _repo_root = _candidate
        except Exception:
            pass  # Fall through — will raise FileNotFoundError below

    cfg_path = os.path.join(_repo_root, "data", "expanded_knowledge_base_preprocessed.csv")
    emb_path = os.path.join(_repo_root, "data", "kb_embeddings_preprocessed.npy")
    out_path = os.path.join(_repo_root, "data", "disease_centroids.npz")

    print("Building disease KB buckets...")
    buckets = build_disease_buckets(cfg_path, emb_path)
    save_disease_buckets(buckets, out_path)

    for disease, indices in buckets.article_indices.items():
        print(f"{disease}: {len(indices)} articles assigned")

    print(f"Centroids saved to {out_path}")
    sys.exit(0)
