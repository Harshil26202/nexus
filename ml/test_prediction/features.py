"""Feature engineering for the test failure prediction model."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestFeatures:
    # File-test relationship signals
    files_changed: int = 0
    test_file_overlap: float = 0.0          # fraction of changed files that directly touch this test's module
    keyword_match_count: int = 0            # how many changed file keywords appear in the test name
    import_graph_distance: float = 1.0      # normalized shortest path in import graph (1.0 = no path found)

    # Historical signals
    historical_failure_rate: float = 0.0    # test's failure rate over last 90 days
    days_since_last_failure: int = 90
    flaky_score: float = 0.0                # fraction of runs that were non-deterministic

    # Change signals
    lines_changed_in_module: int = 0
    has_dependency_change: bool = False
    has_config_change: bool = False

    # Test characteristics
    test_duration_p50_ms: float = 1000.0
    is_integration_test: bool = False
    is_e2e_test: bool = False

    def to_vector(self) -> list[float]:
        return [
            self.files_changed,
            self.test_file_overlap,
            self.keyword_match_count / max(self.files_changed, 1),
            1.0 - self.import_graph_distance,
            self.historical_failure_rate,
            min(self.days_since_last_failure, 90) / 90.0,
            self.flaky_score,
            min(self.lines_changed_in_module, 500) / 500.0,
            int(self.has_dependency_change),
            int(self.has_config_change),
            min(self.test_duration_p50_ms, 60_000) / 60_000.0,
            int(self.is_integration_test),
            int(self.is_e2e_test),
        ]

    @classmethod
    def feature_names(cls) -> list[str]:
        return [
            "files_changed", "test_file_overlap", "keyword_match_ratio",
            "import_proximity", "historical_failure_rate", "last_failure_recency",
            "flaky_score", "lines_changed_norm", "has_dependency_change",
            "has_config_change", "test_duration_norm", "is_integration", "is_e2e",
        ]


def extract_test_features(
    test_name: str,
    test_file: str,
    changed_files: list[str],
    test_history: list[dict[str, Any]],
    module_line_counts: dict[str, int] | None = None,
) -> TestFeatures:
    """Build feature vector for a single (test, diff) pair."""
    feat = TestFeatures()
    feat.files_changed = len(changed_files)

    # Test file overlap
    test_module = test_file.replace("tests/", "").replace("test_", "").replace(".py", "")
    overlap = sum(
        1 for f in changed_files
        if test_module in f.lower() or f.replace("/", "_").replace(".py", "") in test_file.lower()
    )
    feat.test_file_overlap = overlap / max(len(changed_files), 1)

    # Keyword matching
    test_keywords = set(re.split(r"[_/\[\] ]", test_name.lower())) - {"test", ""}
    changed_keywords: set[str] = set()
    for f in changed_files:
        changed_keywords.update(re.split(r"[_/.]", f.lower()))
    feat.keyword_match_count = len(test_keywords & changed_keywords)

    # Historical signals from test history records
    failures = [r for r in test_history if not r.get("passed", True)]
    feat.historical_failure_rate = len(failures) / max(len(test_history), 1)
    if failures:
        from datetime import datetime
        latest_fail = max(r.get("timestamp", 0) for r in failures)
        if isinstance(latest_fail, (int, float)):
            days_ago = (datetime.utcnow().timestamp() - latest_fail) / 86400
            feat.days_since_last_failure = int(days_ago)

    # Flakiness: runs where outcome differs from previous for same commit
    flaky_count = sum(1 for r in test_history if r.get("is_flaky", False))
    feat.flaky_score = flaky_count / max(len(test_history), 1)

    durations = [r.get("duration_ms", 1000) for r in test_history if "duration_ms" in r]
    if durations:
        feat.test_duration_p50_ms = float(sorted(durations)[len(durations) // 2])

    feat.is_integration_test = "integration" in test_file.lower() or "integration" in test_name.lower()
    feat.is_e2e_test = any(kw in test_file.lower() for kw in ("e2e", "end_to_end", "playwright", "cypress"))

    if module_line_counts:
        for changed_file, line_count in module_line_counts.items():
            if test_module in changed_file.lower():
                feat.lines_changed_in_module += line_count

    feat.has_dependency_change = any(
        f in ("requirements.txt", "package.json", "go.mod", "Pipfile") for f in changed_files
    )
    feat.has_config_change = any(
        f.endswith((".yaml", ".yml", ".env", ".toml", ".ini", ".cfg")) for f in changed_files
    )

    return feat
