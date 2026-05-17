"""
Test failure prediction model: XGBoost binary classifier.

Predicts P(test will fail | diff) so NEXUS can skip tests provably unlikely to fail
and prioritize tests most likely to catch the incoming change.

Outputs failure probability in [0, 1]. Threshold default: 0.15.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from .features import TestFeatures, extract_test_features

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "artifacts" / "test_pred_model.ubj"
_CALIBRATOR_PATH = Path(__file__).parent / "artifacts" / "calibrator.pkl"
_model = None
_calibrator = None


def _load_model():
    global _model, _calibrator
    if _model is not None:
        return _model
    try:
        import xgboost as xgb
        if _MODEL_PATH.exists():
            _model = xgb.XGBClassifier()
            _model.load_model(str(_MODEL_PATH))
            logger.info("Loaded XGBoost test prediction model from %s", _MODEL_PATH)
        else:
            logger.warning("Test prediction model artifact not found — using heuristic")
    except ImportError:
        logger.warning("xgboost not installed — using heuristic")
    try:
        import pickle
        if _CALIBRATOR_PATH.exists():
            with open(_CALIBRATOR_PATH, "rb") as f:
                _calibrator = pickle.load(f)
    except Exception:
        pass
    return _model


def _heuristic_probability(feat: TestFeatures) -> float:
    """Rule-based fallback failure probability."""
    score = 0.0
    score += feat.test_file_overlap * 0.40
    score += min(feat.keyword_match_count, 5) / 5.0 * 0.25
    score += feat.historical_failure_rate * 0.20
    score += feat.flaky_score * 0.10
    score += int(feat.has_dependency_change) * 0.05
    return min(score, 0.99)


def predict_batch(
    test_manifest: list[dict[str, Any]],
    changed_files: list[str],
    test_history_by_name: dict[str, list[dict]] | None = None,
    module_line_counts: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """
    Predict failure probability for each test given the current diff.

    Args:
        test_manifest: list of {"name": str, "file": str} dicts
        changed_files: list of changed file paths from the diff
        test_history_by_name: optional map of test_name -> list of historical run records
        module_line_counts: optional map of changed_file -> lines_changed count

    Returns:
        list of {"name", "file", "failure_probability", "should_run"} sorted by probability desc
    """
    model = _load_model()
    test_history_by_name = test_history_by_name or {}
    results = []

    feature_matrix = []
    test_entries = []

    for test in test_manifest:
        name = test["name"]
        file = test.get("file", "")
        history = test_history_by_name.get(name, [])
        feat = extract_test_features(name, file, changed_files, history, module_line_counts)
        feature_matrix.append(feat.to_vector())
        test_entries.append((name, file, feat))

    if model is not None and feature_matrix:
        try:
            X = np.array(feature_matrix, dtype=np.float32)
            probs = model.predict_proba(X)[:, 1]
            if _calibrator is not None:
                probs = _calibrator.transform(probs.reshape(-1, 1)).ravel()
        except Exception as exc:
            logger.warning("Model inference failed (%s) — using heuristic", exc)
            probs = [_heuristic_probability(feat) for _, _, feat in test_entries]
    else:
        probs = [_heuristic_probability(feat) for _, _, feat in test_entries]

    for (name, file, _), prob in zip(test_entries, probs):
        results.append({
            "name": name,
            "file": file,
            "failure_probability": round(float(prob), 4),
            "should_run": float(prob) >= 0.15,
        })

    results.sort(key=lambda x: x["failure_probability"], reverse=True)
    return results
