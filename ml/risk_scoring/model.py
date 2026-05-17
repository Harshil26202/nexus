"""
Risk scoring model: XGBoost gradient-boosted trees trained on historical pipeline data.

Outputs a risk score 0–100. Model is loaded from disk at import time;
falls back to heuristic scoring if the artifact isn't present.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from .features import DiffFeatures, extract_features

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "artifacts" / "risk_model.ubj"
_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        import xgboost as xgb  # type: ignore
        if _MODEL_PATH.exists():
            _model = xgb.XGBRegressor()
            _model.load_model(str(_MODEL_PATH))
            logger.info("Loaded XGBoost risk model from %s", _MODEL_PATH)
        else:
            logger.warning("Risk model artifact not found at %s — using heuristic scorer", _MODEL_PATH)
    except ImportError:
        logger.warning("xgboost not installed — using heuristic scorer")
    return _model


def _heuristic_score(feat: DiffFeatures) -> float:
    """Rule-based fallback when the trained model isn't available."""
    score = 0.0

    # Volume signals
    score += min(feat.files_changed * 1.5, 20)
    score += min((feat.lines_added + feat.lines_deleted) * 0.05, 15)

    # High-impact patterns
    if feat.has_migration:
        score += 25
    if feat.has_schema_change:
        score += 20
    if feat.has_auth_change:
        score += 20
    if feat.has_payment_change:
        score += 25
    if feat.has_infra_change:
        score += 15
    if feat.has_dependency_bump:
        score += 10
    if feat.has_secret_pattern:
        score += 30

    # Temporal amplifiers
    if feat.is_friday:
        score *= 1.25
    if feat.is_after_3pm:
        score *= 1.10

    return min(score, 100.0)


def predict_risk(diff_payload: dict[str, Any], temporal: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return risk score and contributing factors for a GitHub diff payload."""
    feat = extract_features(diff_payload)
    if temporal:
        feat.is_friday = temporal.get("is_friday", False)
        feat.is_after_3pm = temporal.get("is_after_3pm", False)
        feat.hour_utc = temporal.get("hour_utc", 12)
        feat.days_since_last_incident = temporal.get("days_since_last_incident", 30)

    model = _load_model()
    if model is not None:
        try:
            vec = np.array([feat.to_vector()], dtype=np.float32)
            raw = float(model.predict(vec)[0])
            score = float(np.clip(raw, 0, 100))
        except Exception as exc:
            logger.warning("Model inference failed (%s) — falling back to heuristic", exc)
            score = _heuristic_score(feat)
    else:
        score = _heuristic_score(feat)

    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"

    risk_factors: list[str] = []
    if feat.has_migration:
        risk_factors.append("Database migration detected")
    if feat.has_schema_change:
        risk_factors.append("Schema change in models")
    if feat.has_auth_change:
        risk_factors.append("Authentication/authorization code modified")
    if feat.has_payment_change:
        risk_factors.append("Payment/billing code modified")
    if feat.has_infra_change:
        risk_factors.append("Infrastructure configuration changed")
    if feat.has_dependency_bump:
        risk_factors.append("Dependency version bump")
    if feat.has_secret_pattern:
        risk_factors.append("Potential secret/credential pattern in diff")
    if feat.is_friday and feat.is_after_3pm:
        risk_factors.append("Friday afternoon deploy — high blast radius window")

    return {
        "score": round(score, 1),
        "level": level,
        "risk_factors": risk_factors,
        "features": {
            "files_changed": feat.files_changed,
            "lines_changed": feat.lines_added + feat.lines_deleted,
            "has_migration": feat.has_migration,
            "has_auth_change": feat.has_auth_change,
            "has_payment_change": feat.has_payment_change,
        },
    }
