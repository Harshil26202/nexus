"""Tests for ML test failure prediction service."""
import pytest
from app.services.ml_service import ml_service, TestFailurePredictionService


MANIFEST = [
    {"name": "test_payment_checkout", "path": "tests/test_checkout.py", "tags": ["payment", "unit"], "avg_duration_ms": 200},
    {"name": "test_auth_login",       "path": "tests/test_auth.py",     "tags": ["auth", "unit"],    "avg_duration_ms": 150},
    {"name": "test_unrelated_config", "path": "tests/test_config.py",   "tags": ["config"],          "avg_duration_ms": 50},
]


def test_predict_returns_all_tests():
    preds = ml_service.predict(["app/payments/checkout.py"], MANIFEST)
    assert len(preds) == len(MANIFEST)


def test_payment_change_scores_payment_tests_higher():
    preds = ml_service.predict(["app/payments/processor.py"], MANIFEST)
    payment_pred = next(p for p in preds if "payment" in p.test_name)
    config_pred  = next(p for p in preds if "config"  in p.test_name)
    assert payment_pred.failure_probability > config_pred.failure_probability


def test_auth_change_scores_auth_tests_higher():
    preds = ml_service.predict(["app/auth/jwt.py"], MANIFEST)
    auth_pred    = next(p for p in preds if "auth" in p.test_name)
    config_pred  = next(p for p in preds if "config" in p.test_name)
    assert auth_pred.failure_probability > config_pred.failure_probability


def test_select_tests_splits_correctly():
    must_run, skip = ml_service.select_tests(
        changed_files=["app/payments/processor.py"],
        test_manifest=MANIFEST,
        threshold=0.15,
    )
    # At least the payment test should be in must_run
    all_selected = [t["name"] for t in must_run]
    assert "test_payment_checkout" in all_selected


def test_select_tests_total_equals_manifest():
    must_run, skip = ml_service.select_tests(
        changed_files=["app/payments/processor.py"],
        test_manifest=MANIFEST,
    )
    assert len(must_run) + len(skip) == len(MANIFEST)


def test_probability_range():
    preds = ml_service.predict(["app/payments/processor.py"], MANIFEST)
    for p in preds:
        assert 0.0 <= p.failure_probability <= 1.0


def test_deterministic_output():
    preds1 = ml_service.predict(["app/payments/processor.py"], MANIFEST)
    preds2 = ml_service.predict(["app/payments/processor.py"], MANIFEST)
    for p1, p2 in zip(preds1, preds2):
        assert p1.failure_probability == p2.failure_probability
