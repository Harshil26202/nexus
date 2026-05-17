import uuid
from enum import Enum

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Pipeline(Base):
    __tablename__ = "pipelines"

    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    commit_message: Mapped[str] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[PipelineStatus] = mapped_column(
        String(20), default=PipelineStatus.PENDING, nullable=False
    )
    risk_level: Mapped[RiskLevel | None] = mapped_column(String(20), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # AI analysis outputs
    semantic_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    blast_radius: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    selected_tests: Mapped[list | None] = mapped_column(JSON, nullable=True)
    skipped_tests: Mapped[list | None] = mapped_column(JSON, nullable=True)
    gate_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    runs: Mapped[list["PipelineRun"]] = relationship(back_populates="pipeline")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PipelineStatus] = mapped_column(String(20), nullable=False)
    log_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="runs")
