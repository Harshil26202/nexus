"""
Training script for the XGBoost risk scoring model.

Usage:
    python -m ml.risk_scoring.train --data data/pipeline_history.jsonl --output artifacts/risk_model.ubj

The training dataset is a JSONL file where each line is:
    {"diff_payload": {...}, "temporal": {...}, "actual_risk_score": 72.5}

actual_risk_score is the ground-truth label (0–100) derived from:
  - Post-deploy incident rate for this pipeline
  - Time-to-revert if a rollback occurred
  - Human-annotated severity from the incident log
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import numpy as np

from .features import extract_features

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_dataset(path: str) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    with open(path) as f:
        for line in f:
            record = json.loads(line)
            feat = extract_features(record["diff_payload"])
            temporal = record.get("temporal", {})
            feat.is_friday = temporal.get("is_friday", False)
            feat.is_after_3pm = temporal.get("is_after_3pm", False)
            feat.hour_utc = temporal.get("hour_utc", 12)
            feat.days_since_last_incident = temporal.get("days_since_last_incident", 30)
            X.append(feat.to_vector())
            y.append(float(record["actual_risk_score"]))
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def train(data_path: str, output_path: str, n_estimators: int = 400, max_depth: int = 6) -> None:
    try:
        import xgboost as xgb
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error, r2_score
    except ImportError:
        raise SystemExit("Install xgboost and scikit-learn: pip install xgboost scikit-learn")

    logger.info("Loading dataset from %s", data_path)
    X, y = load_dataset(data_path)
    logger.info("Dataset: %d samples, %d features", len(X), X.shape[1])

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="reg:squarederror",
        eval_metric="mae",
        early_stopping_rounds=30,
        n_jobs=-1,
        random_state=42,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    preds = model.predict(X_val)
    preds = np.clip(preds, 0, 100)
    mae = mean_absolute_error(y_val, preds)
    r2 = r2_score(y_val, preds)
    logger.info("Validation MAE: %.2f  R²: %.4f", mae, r2)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(out))
    logger.info("Model saved to %s", out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train NEXUS risk scoring model")
    parser.add_argument("--data", required=True, help="Path to JSONL training dataset")
    parser.add_argument("--output", default="ml/risk_scoring/artifacts/risk_model.ubj")
    parser.add_argument("--estimators", type=int, default=400)
    parser.add_argument("--depth", type=int, default=6)
    args = parser.parse_args()
    train(args.data, args.output, args.estimators, args.depth)


if __name__ == "__main__":
    main()
