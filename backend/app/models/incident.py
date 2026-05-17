from enum import Enum

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IncidentSeverity(str, Enum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class Incident(Base):
    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(String(10), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        String(20), default=IncidentStatus.OPEN, nullable=False
    )
    service: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), default="production")

    # AI-generated fields
    root_cause_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    root_cause_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    postmortem_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_services: Mapped[list | None] = mapped_column(JSON, nullable=True)
    timeline: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Integration references
    pagerduty_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    github_issue_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_thread_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    resolved_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mttr_seconds: Mapped[int | None] = mapped_column(
        __import__("sqlalchemy", fromlist=["Integer"]).Integer, nullable=True
    )
