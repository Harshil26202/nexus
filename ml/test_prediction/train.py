"""
Training script for the XGBoost test failure prediction model.

Usage:
    python -m ml.test_prediction.train --data data/test_history.jsonl --output artifacts/test_pred_model.ubj

Training dataset JSONL schema:
    {
        "test_name": "test_payment_charge_success",
        "test_file": "tests/test_payments.py",
        "changed_files": ["app/services/payment_service.py", "requirements.txt"],
        "test_history": [{"passed": true, "duration_ms": 340, "timestamp": 1700000000}],
        "module_line_counts": {"app/services/payment_service.py": 42},
        "label": 1   // 1 = test failed in this run, 0 = passed
    }
"""
from __future__ import annotations

import argparse
import json
import logging
import pickle
from pathlib import Path

import numpy as np

from .features import extract_test_features

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_dataset(path: str) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            feat = extract_test_features(
                test_name=r["test_name"],
                test_file=r.get("test_file", ""),
                changed_files=r.get("changed_files", []),
                test_history=r.get("test_history", []),
                module_line_counts=r.get("module_line_counts"),
            )
            X.append(feat.to_vector())
            y.append(int(r["label"]))
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def train(data_path: str, output_path: str, n_estimators: int = 500, max_depth: int = 5) -> None:
    try:
        import xgboost as xgb
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, average_precision_score, classification_report
    except ImportError:
        raise SystemExit("Install: pip install xgboost scikit-learn")

    logger.info("Loading dataset from %s", data_path)
    X, y = load_dataset(data_path)
    pos_rate = y.mean()
    scale = (1 - pos_rate) / max(pos_rate, 1e-6)
    logger.info("Dataset: %d samples  pos_rate=%.2f%%  scale_pos_weight=%.1f", len(X), pos_rate * 100, scale)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    model = xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        scale_pos_weight=scale,
        objective="binary:logistic",
        eval_metric="aucpr",
        early_stopping_rounds=40,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)

    probs = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, probs)
    ap = average_precision_score(y_val, probs)
    logger.info("Validation AUC-ROC: %.4f  AP: %.4f", auc, ap)
    logger.info("\n%s", classification_report(y_val, (probs >= 0.15).astype(int)))

    # Platt scaling calibration
    calibrated = CalibratedClassifierCV(model, cv="prefit", method="sigmoid")
    calibrated.fit(X_val, y_val)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(out))
    cal_path = out.parent / "calibrator.pkl"
    with open(cal_path, "wb") as f:
        pickle.dump(calibrated.calibrated_classifiers_[0].calibrator, f)

    logger.info("Model saved to %s", out)
    logger.info("Calibrator saved to %s", cal_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train NEXUS test failure prediction model")
    parser.add_argument("--data", required=True, help="Path to JSONL training dataset")
    parser.add_argument("--output", default="ml/test_prediction/artifacts/test_pred_model.ubj")
    parser.add_argument("--estimators", type=int, default=500)
    parser.add_argument("--depth", type=int, default=5)
    args = parser.parse_args()
    train(args.data, args.output, args.estimators, args.depth)


if __name__ == "__main__":
    main()
