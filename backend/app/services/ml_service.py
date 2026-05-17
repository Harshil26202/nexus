"""Test Failure Prediction ML Service.

Uses a lightweight XGBoost model trained on historical CI data to predict
which tests are likely to fail given a set of changed files.

In production this model is served from Azure ML. For the demo we use
a rule-based heuristic that simulates the ML output.
"""
import hashlib
from dataclasses import dataclass

import structlog

log = structlog.get_logger()


@dataclass
class TestPrediction:
    test_name: str
    test_path: str
    failure_probability: float  # 0.0 – 1.0
    reason: str


class TestFailurePredictionService:
    """Predicts test failure probability based on changed files.

    Production: load model from Azure ML endpoint.
    Demo: deterministic heuristic that maps file→test relationships.
    """

    # File prefix → test tag mappings (simulating learned relationships)
    _FILE_TEST_MAP: dict[str, list[str]] = {
        "payment":      ["payment", "checkout", "transaction", "refund"],
        "auth":         ["auth", "login", "session", "jwt", "oauth"],
        "user":         ["user", "profile", "account", "registration"],
        "notification": ["notification", "email", "sms", "webhook"],
        "api":          ["api", "integration", "e2e"],
        "db":           ["db", "migration", "schema"],
        "config":       [],
    }

    def predict(self, changed_files: list[str], test_manifest: list[dict]) -> list[TestPrediction]:
        """Return failure probability for each test given changed files."""
        affected_keywords: set[str] = set()
        for f in changed_files:
            fname = f.lower()
            for keyword, tags in self._FILE_TEST_MAP.items():
                if keyword in fname:
                    affected_keywords.update(tags)

        predictions = []
        for test in test_manifest:
            name = test.get("name", "").lower()
            tags = [t.lower() for t in test.get("tags", [])]

            # Score based on name/tag overlap with changed areas
            overlap = sum(1 for kw in affected_keywords if kw in name or any(kw in t for t in tags))
            base_prob = min(0.05 + overlap * 0.25, 0.95)

            # Add deterministic noise from test name hash (simulates model variance)
            noise = (int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % 100) / 1000.0
            prob = min(base_prob + noise, 1.0)

            reason = (
                f"Directly exercises {', '.join(affected_keywords & set(name.split('_')))}"
                if overlap > 0
                else "No overlap with changed files detected"
            )

            predictions.append(TestPrediction(
                test_name=test.get("name", ""),
                test_path=test.get("path", ""),
                failure_probability=round(prob, 3),
                reason=reason,
            ))

        return sorted(predictions, key=lambda p: p.failure_probability, reverse=True)

    def select_tests(
        self,
        changed_files: list[str],
        test_manifest: list[dict],
        threshold: float = 0.15,
    ) -> tuple[list[dict], list[dict]]:
        """Split test manifest into must-run and skip lists."""
        predictions = self.predict(changed_files, test_manifest)
        must_run, skip = [], []

        for pred in predictions:
            test_entry = {
                "name": pred.test_name,
                "path": pred.test_path,
                "failure_probability": pred.failure_probability,
                "reason": pred.reason,
            }
            if pred.failure_probability >= threshold:
                must_run.append(test_entry)
            else:
                skip.append({**test_entry, "reason": "Below failure probability threshold"})

        log.info(
            "ml.test_selection",
            total=len(test_manifest),
            must_run=len(must_run),
            skipped=len(skip),
            threshold=threshold,
        )
        return must_run, skip


ml_service = TestFailurePredictionService()
