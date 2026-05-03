"""
Disease Evaluator
=================

Builds per-disease dataset splits (train / tune / holdout) from knowledge-base
articles, runs the full verifier pipeline over holdout articles, and produces
a per-disease evaluation report with precision and accuracy metrics.

This module implements FOCUS-03 requirements for a reproducible benchmark report:
  - DiseaseSplits dataclass + build_disease_splits() — deterministic stratified splits
  - save_splits() / load_splits() — JSON persistence for reproducibility
  - DiseaseEvaluator — orchestrates split construction and evaluation runs
  - outputs/disease_eval_report.json — per-disease precision + accuracy + gate status

Usage (CLI — builds splits only, no verifier needed):
    python src/disease_evaluator.py

Usage (API — full evaluation):
    from disease_evaluator import DiseaseEvaluator
    evaluator = DiseaseEvaluator()
    report = evaluator.run_full_eval()
"""

import os
import json
import math
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd

from medical_config import get_global_config
from disease_buckets import DiseaseKBBuckets, build_disease_buckets, load_disease_buckets


# --------------------------------------------------------------------------- #
# DiseaseSplits dataclass
# --------------------------------------------------------------------------- #

@dataclass
class DiseaseSplits:
    """Per-disease train/tune/holdout article index splits.

    Attributes:
        train:       disease -> KB row indices for training (60%)
        tune:        disease -> KB row indices for tuning (20%)
        holdout:     disease -> KB row indices for holdout evaluation (20%)
        random_seed: DISEASE_RANDOM_SEED value used for the shuffle
        built_at:    ISO 8601 UTC timestamp when splits were constructed
    """
    train: Dict[str, List[int]]    = field(default_factory=dict)
    tune: Dict[str, List[int]]     = field(default_factory=dict)
    holdout: Dict[str, List[int]]  = field(default_factory=dict)
    random_seed: int = 42
    built_at: str = ""


# --------------------------------------------------------------------------- #
# build_disease_splits
# --------------------------------------------------------------------------- #

def build_disease_splits(
    buckets: DiseaseKBBuckets,
    kb_csv_path: str,
    config=None,
) -> DiseaseSplits:
    """Build per-disease stratified train/tune/holdout splits from KB article indices.

    Strategy (D-05):
    - Stratify by confidence tier derived from tertile binning of quality_score values
      within each disease bucket (top-33% = high, mid-33% = medium, bottom-34% = low).
    - Shuffle each tier independently using DISEASE_RANDOM_SEED for reproducibility.
    - Holdout fraction ~20%, tune fraction ~20%, train fraction ~60% (rounded up).

    Args:
        buckets:     DiseaseKBBuckets produced by build_disease_buckets / load_disease_buckets.
        kb_csv_path: Path to expanded_knowledge_base_preprocessed.csv (needs quality_score).
        config:      Optional ConfigurationSettings; defaults to global config.

    Returns:
        DiseaseSplits with train/tune/holdout dicts per disease, no index overlaps.
    """
    cfg = config or get_global_config()
    dc = cfg.get_disease_config()

    rng = np.random.default_rng(dc['random_seed'])

    # Load only the quality_score column — efficient for large CSVs
    kb_quality = pd.read_csv(kb_csv_path, usecols=['quality_score'])['quality_score'].values

    train: Dict[str, List[int]] = {}
    tune: Dict[str, List[int]] = {}
    holdout: Dict[str, List[int]] = {}

    for disease in dc['disease_list']:
        indices = np.array(sorted(buckets.article_indices[disease]))

        if len(indices) == 0:
            train[disease] = []
            tune[disease] = []
            holdout[disease] = []
            continue

        quality = kb_quality[indices]

        # Tertile thresholds — ensures all 3 tiers are populated even when
        # all quality_scores fall in the same absolute band (e.g., 0.30–0.775)
        t33 = np.percentile(quality, 33.33)
        t67 = np.percentile(quality, 66.67)

        # Assign tier labels using vectorised where
        # "high" = top 33%, "medium" = mid 33%, "low" = bottom 34%
        tier_labels = np.where(
            quality >= t67, 'high',
            np.where(quality >= t33, 'medium', 'low')
        )

        tier_holdout: List[int] = []
        tier_tune: List[int] = []
        tier_train: List[int] = []

        for tier in ('high', 'medium', 'low'):
            tier_mask = tier_labels == tier
            tier_idx = indices[tier_mask].copy()  # copy before in-place shuffle

            rng.shuffle(tier_idx)

            n = len(tier_idx)
            n_holdout = max(1, math.ceil(n * dc['holdout_fraction']))
            n_tune = max(1, math.ceil(n * dc['tune_fraction']))
            # Ensure at least 1 article remains for train; clamp if bucket is tiny
            n_train = n - n_holdout - n_tune
            if n_train < 1:
                # When bucket is tiny (2-3 articles), reduce tune then holdout
                n_tune = max(0, n_tune - 1)
                n_train = n - n_holdout - n_tune
                if n_train < 0:
                    n_train = 0

            tier_holdout.extend(tier_idx[:n_holdout].tolist())
            tier_tune.extend(tier_idx[n_holdout:n_holdout + n_tune].tolist())
            tier_train.extend(tier_idx[n_holdout + n_tune:].tolist())

        # Sort for deterministic ordering and easy dedup verification
        holdout[disease] = sorted(tier_holdout)
        tune[disease] = sorted(tier_tune)
        train[disease] = sorted(tier_train)

    return DiseaseSplits(
        train=train,
        tune=tune,
        holdout=holdout,
        random_seed=dc['random_seed'],
        built_at=datetime.utcnow().isoformat() + 'Z',
    )


# --------------------------------------------------------------------------- #
# save_splits / load_splits
# --------------------------------------------------------------------------- #

def save_splits(splits: DiseaseSplits, path: str) -> None:
    """Serialize DiseaseSplits to a JSON file at ``path``.

    Lists are stored as plain JSON arrays. Creates parent directories if needed.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = {
        'train': splits.train,
        'tune': splits.tune,
        'holdout': splits.holdout,
        'random_seed': splits.random_seed,
        'built_at': splits.built_at,
    }
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2)


def load_splits(path: str) -> DiseaseSplits:
    """Load DiseaseSplits from a JSON file previously written by save_splits().

    Args:
        path: Path to disease_splits.json.

    Returns:
        DiseaseSplits with all fields restored from JSON.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Disease splits file not found: {path}")

    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    # JSON stores list-of-int as plain lists; type is preserved
    return DiseaseSplits(
        train=data.get('train', {}),
        tune=data.get('tune', {}),
        holdout=data.get('holdout', {}),
        random_seed=data.get('random_seed', 42),
        built_at=data.get('built_at', ''),
    )


# --------------------------------------------------------------------------- #
# DiseaseEvaluator
# --------------------------------------------------------------------------- #

class DiseaseEvaluator:
    """Evaluate per-disease hallucination detection performance on KB holdout articles.

    Orchestrates:
    1. ensure_buckets()  — load or build disease KB centroids/article buckets
    2. ensure_splits()   — load or build stratified train/tune/holdout splits
    3. evaluate_disease() — run verify_for_disease() on holdout articles; compute
                            precision and accuracy against known-good KB content
    4. run_full_eval()   — iterate all diseases, write outputs/disease_eval_report.json
    5. check_gate_pass() — returns True iff all diseases meet precision + accuracy targets
    """

    def __init__(
        self,
        kb_csv_path: str = None,
        embeddings_path: str = None,
        centroids_path: str = None,
        splits_path: str = None,
        config=None,
    ) -> None:
        self.cfg = config or get_global_config()
        self.dc = self.cfg.get_disease_config()

        # Resolve default paths relative to this file's parent (src/ -> repo root)
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        self.kb_csv_path = kb_csv_path or os.path.normpath(
            os.path.join(base, 'data', 'expanded_knowledge_base_preprocessed.csv')
        )
        self.embeddings_path = embeddings_path or os.path.normpath(
            os.path.join(base, 'data', 'kb_embeddings_preprocessed.npy')
        )
        self.centroids_path = centroids_path or os.path.normpath(
            os.path.join(base, 'data', 'disease_centroids.npz')
        )
        self.splits_path = splits_path or os.path.normpath(
            os.path.join(base, 'data', 'disease_splits.json')
        )

        self.buckets: Optional[DiseaseKBBuckets] = None
        self.splits: Optional[DiseaseSplits] = None

    # ---------------------------------------------------------------------- #
    # Lazy loaders
    # ---------------------------------------------------------------------- #

    def ensure_buckets(self) -> DiseaseKBBuckets:
        """Load disease_centroids.npz if it exists; otherwise build from scratch."""
        if self.buckets is None:
            if os.path.exists(self.centroids_path):
                self.buckets = load_disease_buckets(self.centroids_path)
            else:
                self.buckets = build_disease_buckets(
                    self.kb_csv_path, self.embeddings_path, self.cfg
                )
        return self.buckets

    def ensure_splits(self) -> DiseaseSplits:
        """Load disease_splits.json if it exists; otherwise build and save."""
        if self.splits is None:
            if os.path.exists(self.splits_path):
                self.splits = load_splits(self.splits_path)
            else:
                buckets = self.ensure_buckets()
                self.splits = build_disease_splits(buckets, self.kb_csv_path, self.cfg)
                save_splits(self.splits, self.splits_path)
        return self.splits

    # ---------------------------------------------------------------------- #
    # Per-disease evaluation
    # ---------------------------------------------------------------------- #

    def evaluate_disease(self, disease: str, verifier=None) -> Dict[str, Any]:
        """Run the full verifier pipeline over holdout articles for a single disease.

        Ground truth assumption:
            All holdout articles are known-good KB content (verified medical content,
            not hallucinations). A result is CORRECT if the verifier does NOT flag the
            article as CRITICAL_RISK or HIGH_RISK (i.e., it correctly accepts the article).

        Proxy metrics (all-negative ground truth, no true positives possible):
            precision = not_flagged / total  — proportion correctly not flagged
            accuracy  = not_flagged / total  — identical for all-negative ground truth

        Uses verify_for_disease() (D-04 hybrid path: disease-filtered FAISS retrieval
        AND disease-specific Layer 1 patterns applied together).

        Args:
            disease:  Disease slug (must exist in dc['disease_list']).
            verifier: Optional MedicalVerifier instance. Created lazily if None.

        Returns:
            Dict with keys:
              disease, total_holdout, flagged_count, not_flagged_count,
              precision, accuracy, target_precision, target_accuracy, gate_pass
        """
        splits = self.ensure_splits()
        holdout_indices = splits.holdout.get(disease, [])
        if not holdout_indices:
            return {
                'disease': disease,
                'error': 'no holdout articles',
                'gate_pass': False,
            }

        # Load KB article texts for holdout rows
        kb = pd.read_csv(self.kb_csv_path, usecols=['text', 'normalized_text'])
        kb_texts = kb['normalized_text'].fillna(kb['text']).tolist()

        # Lazy verifier instantiation — avoids heavy model load when only splits needed
        if verifier is None:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from medical_verifier import MedicalVerifier  # noqa: PLC0415
            verifier = MedicalVerifier()

        # Ensure buckets are loaded (needed for verify_for_disease)
        buckets = self.ensure_buckets()

        flagged = 0
        total = len(holdout_indices)

        for rank, idx in enumerate(holdout_indices):
            text = str(kb_texts[idx]) if idx < len(kb_texts) else ""
            if not text.strip():
                # Empty text cannot be verified — treat as flagged (conservative)
                flagged += 1
                continue
            try:
                # D-04: use verify_for_disease(), NOT verify_single_summary()
                # Both retrieval filtering and disease rule patterns fire together.
                result = verifier.verify_for_disease(
                    text,
                    disease=disease,
                    buckets=buckets,
                    summary_id=f"{disease}_holdout_{rank}",
                )
                level = result.get('risk_assessment', {}).get('level', 'UNKNOWN')
                if level in ('CRITICAL_RISK', 'HIGH_RISK'):
                    flagged += 1
            except Exception:
                # Count failed verifications as flagged (conservative fallback)
                flagged += 1

        not_flagged = total - flagged
        precision = not_flagged / total if total > 0 else 0.0
        accuracy = not_flagged / total if total > 0 else 0.0
        gate_pass = (
            precision >= self.dc['precision_target']
            and accuracy >= self.dc['accuracy_target']
        )

        return {
            'disease': disease,
            'total_holdout': total,
            'flagged_count': flagged,
            'not_flagged_count': not_flagged,
            'precision': round(precision, 4),
            'accuracy': round(accuracy, 4),
            'target_precision': self.dc['precision_target'],
            'target_accuracy': self.dc['accuracy_target'],
            'gate_pass': gate_pass,
        }

    # ---------------------------------------------------------------------- #
    # Full evaluation run
    # ---------------------------------------------------------------------- #

    def run_full_eval(self, verifier=None, output_path: str = None) -> Dict[str, Any]:
        """Evaluate all diseases and write the report to outputs/disease_eval_report.json.

        Iterates dc['disease_list'], calls evaluate_disease() per disease, aggregates
        results, and writes a JSON report that includes:
          - per-disease precision, accuracy, and gate_pass
          - all_gate_pass — True iff every disease passes individually
          - eval_timestamp — ISO 8601 UTC
          - config_snapshot — dc dict for audit trail (T-05-09 mitigation)

        Args:
            verifier:    Optional shared MedicalVerifier instance (avoids multiple loads).
            output_path: Optional override for report destination path.

        Returns:
            The report dict (same content as written to JSON).
        """
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        out_path = output_path or os.path.normpath(
            os.path.join(base, 'outputs', 'disease_eval_report.json')
        )

        results: Dict[str, Any] = {}
        for disease in self.dc['disease_list']:
            results[disease] = self.evaluate_disease(disease, verifier=verifier)

        report: Dict[str, Any] = {
            'eval_timestamp': datetime.utcnow().isoformat() + 'Z',
            'disease_results': results,
            'all_gate_pass': all(
                r.get('gate_pass', False) for r in results.values()
            ),
            'config_snapshot': self.dc,
        }

        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as fh:
            json.dump(report, fh, indent=2)
        print(f"Eval report written to: {out_path}")
        return report

    # ---------------------------------------------------------------------- #
    # Gate check
    # ---------------------------------------------------------------------- #

    def check_gate_pass(self, report: Dict[str, Any]) -> bool:
        """Return True if ALL diseases in the report meet precision and accuracy targets.

        Args:
            report: Dict returned by run_full_eval().

        Returns:
            True iff report['all_gate_pass'] is True (all per-disease gate_pass flags set).
        """
        return bool(report.get('all_gate_pass', False))


# --------------------------------------------------------------------------- #
# CLI entrypoint — builds splits only (full eval with verifier is slow)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys

    # Resolve paths relative to repo root. When running in a git worktree,
    # large data artifacts live in the main repo; fall back via git common dir.
    _src_dir = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_src_dir)

    _kb_check = os.path.join(_repo_root, 'data', 'expanded_knowledge_base_preprocessed.csv')
    if not os.path.isfile(_kb_check):
        import subprocess  # noqa: PLC0415
        try:
            _git_common = subprocess.check_output(
                ['git', 'rev-parse', '--git-common-dir'],
                cwd=_src_dir,
                text=True,
            ).strip()
            _candidate = os.path.dirname(os.path.abspath(_git_common))
            _candidate_csv = os.path.join(
                _candidate, 'data', 'expanded_knowledge_base_preprocessed.csv'
            )
            if os.path.isfile(_candidate_csv):
                _repo_root = _candidate
        except Exception:
            pass  # Will raise FileNotFoundError when paths are used

    _kb_csv = os.path.join(_repo_root, 'data', 'expanded_knowledge_base_preprocessed.csv')
    _emb = os.path.join(_repo_root, 'data', 'kb_embeddings_preprocessed.npy')
    _centroids = os.path.join(_repo_root, 'data', 'disease_centroids.npz')
    _splits = os.path.join(_repo_root, 'data', 'disease_splits.json')

    evaluator = DiseaseEvaluator(
        kb_csv_path=_kb_csv,
        embeddings_path=_emb,
        centroids_path=_centroids,
        splits_path=_splits,
    )
    splits = evaluator.ensure_splits()
    print("Splits built and saved to:", evaluator.splits_path)
    for disease in evaluator.dc['disease_list']:
        print(
            f"  {disease}: holdout={len(splits.holdout[disease])}, "
            f"train={len(splits.train[disease])}, tune={len(splits.tune[disease])}"
        )
    sys.exit(0)
