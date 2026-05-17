import uuid
from enum import Enum

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    SEMANTIC_ANALYZER = "semantic_analyzer"
    TEST_INTELLIGENCE = "test_intelligence"
    QUALITY_GATE = "quality_gate"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    INCIDENT_RESPONSE = "incident_response"
    NL_DEVOPS = "nl_devops"


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=True, index=True
    )
    agent_type: Mapped[AgentType] = mapped_column(String(50), nullable=False)
    status: Mapped[AgentTaskStatus] = mapped_column(
        String(20), default=AgentTaskStatus.QUEUED, nullable=False
    )

    input_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agent execution trace — every tool call and reasoning step
    execution_trace: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(
        __import__("sqlalchemy", fromlist=["Integer"]).Integer, nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=True
    )
