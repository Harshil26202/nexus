from enum import Enum

from sqlalchemy import JSON, Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GateType(str, Enum):
    COVERAGE = "coverage"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLEXITY = "complexity"
    CUSTOM_AI = "custom_ai"


class QualityGate(Base):
    __tablename__ = "quality_gates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_pattern: Mapped[str] = mapped_column(String(255), default="*")
    gate_type: Mapped[GateType] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Static thresholds (baseline)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_operator: Mapped[str] = mapped_column(String(10), default="gte")

    # AI-adaptive config
    adaptive_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    adaptive_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
