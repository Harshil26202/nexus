"""Feature engineering for the code change risk scoring model."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffFeatures:
    # File-level
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    files_by_type: dict[str, int] = field(default_factory=dict)

    # Semantic signals
    has_migration: bool = False
    has_schema_change: bool = False
    has_auth_change: bool = False
    has_payment_change: bool = False
    has_infra_change: bool = False
    has_dependency_bump: bool = False
    has_secret_pattern: bool = False

    # Code complexity signals
    cyclomatic_delta: float = 0.0
    test_coverage_delta: float = 0.0
    new_endpoints: int = 0
    removed_endpoints: int = 0

    # Temporal signals (filled by caller)
    is_friday: bool = False
    is_after_3pm: bool = False
    hour_utc: int = 12
    days_since_last_incident: int = 30

    def to_vector(self) -> list[float]:
        type_counts = [
            self.files_by_type.get(ext, 0)
            for ext in (".py", ".ts", ".tsx", ".js", ".tf", ".yaml", ".yml", ".sql")
        ]
        return [
            self.files_changed,
            self.lines_added,
            self.lines_deleted,
            self.lines_added / max(self.lines_deleted, 1),
            *type_counts,
            int(self.has_migration),
            int(self.has_schema_change),
            int(self.has_auth_change),
            int(self.has_payment_change),
            int(self.has_infra_change),
            int(self.has_dependency_bump),
            int(self.has_secret_pattern),
            self.cyclomatic_delta,
            self.test_coverage_delta,
            self.new_endpoints,
            self.removed_endpoints,
            int(self.is_friday),
            int(self.is_after_3pm),
            self.hour_utc / 24.0,
            min(self.days_since_last_incident, 90) / 90.0,
        ]

    @classmethod
    def feature_names(cls) -> list[str]:
        type_names = [f"files_{ext[1:]}" for ext in (".py", ".ts", ".tsx", ".js", ".tf", ".yaml", ".yml", ".sql")]
        return [
            "files_changed", "lines_added", "lines_deleted", "add_del_ratio",
            *type_names,
            "has_migration", "has_schema_change", "has_auth_change", "has_payment_change",
            "has_infra_change", "has_dependency_bump", "has_secret_pattern",
            "cyclomatic_delta", "test_coverage_delta", "new_endpoints", "removed_endpoints",
            "is_friday", "is_after_3pm", "hour_utc_norm", "incident_recency_norm",
        ]


_SECRET_PATTERNS = re.compile(
    r'(password|secret|api_key|token|private_key|credential)\s*=\s*["\'][^"\']{8,}',
    re.IGNORECASE,
)
_MIGRATION_EXTS = {".sql", ".migration"}
_AUTH_KEYWORDS = {"auth", "login", "oauth", "jwt", "session", "permission", "rbac", "role"}
_PAYMENT_KEYWORDS = {"payment", "billing", "stripe", "invoice", "charge", "subscription", "checkout"}
_INFRA_EXTS = {".tf", ".tfvars", ".yaml", ".yml"}
_INFRA_DIRS = {"kubernetes", "k8s", "terraform", "helm", "infrastructure", "deploy"}


def extract_features(diff_payload: dict[str, Any]) -> DiffFeatures:
    """Extract ML features from a GitHub diff payload dict."""
    files: list[dict] = diff_payload.get("files", [])
    feat = DiffFeatures()
    feat.files_changed = len(files)

    for f in files:
        filename: str = f.get("filename", "")
        additions: int = f.get("additions", 0)
        deletions: int = f.get("deletions", 0)
        patch: str = f.get("patch", "") or ""

        feat.lines_added += additions
        feat.lines_deleted += deletions

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        feat.files_by_type[ext] = feat.files_by_type.get(ext, 0) + 1

        parts = set(filename.lower().replace("/", " ").replace("_", " ").split())

        if ext in _MIGRATION_EXTS or "migration" in filename.lower() or "migrate" in filename.lower():
            feat.has_migration = True
        if "schema" in filename.lower() or "models" in filename.lower():
            feat.has_schema_change = True
        if parts & _AUTH_KEYWORDS:
            feat.has_auth_change = True
        if parts & _PAYMENT_KEYWORDS:
            feat.has_payment_change = True
        if ext in _INFRA_EXTS and any(d in filename.lower() for d in _INFRA_DIRS):
            feat.has_infra_change = True
        if filename in ("requirements.txt", "package.json", "go.mod", "Pipfile", "pyproject.toml"):
            feat.has_dependency_bump = True
        if _SECRET_PATTERNS.search(patch):
            feat.has_secret_pattern = True

        # Count new REST endpoints (simple heuristic for Python/TS)
        feat.new_endpoints += len(re.findall(r'^\+.*@(?:app|router)\.(get|post|put|delete|patch)\(', patch, re.M))
        feat.removed_endpoints += len(re.findall(r'^-.*@(?:app|router)\.(get|post|put|delete|patch)\(', patch, re.M))

    return feat
