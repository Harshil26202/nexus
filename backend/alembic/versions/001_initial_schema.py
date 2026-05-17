"""Initial schema — all NEXUS tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pipelines
    op.create_table(
        "pipelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("repo_full_name",  sa.String(255), nullable=False),
        sa.Column("branch",          sa.String(255), nullable=False),
        sa.Column("commit_sha",      sa.String(40),  nullable=False),
        sa.Column("commit_message",  sa.Text),
        sa.Column("author",          sa.String(255)),
        sa.Column("pr_number",       sa.Integer),
        sa.Column("status",          sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("risk_level",      sa.String(20)),
        sa.Column("risk_score",      sa.Float),
        sa.Column("semantic_summary", sa.Text),
        sa.Column("blast_radius",    JSON),
        sa.Column("selected_tests",  JSON),
        sa.Column("skipped_tests",   JSON),
        sa.Column("gate_results",    JSON),
        sa.Column("ai_recommendation", sa.Text),
        sa.Column("started_at",      sa.String(50)),
        sa.Column("finished_at",     sa.String(50)),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pipelines_repo",       "pipelines", ["repo_full_name"])
    op.create_index("ix_pipelines_commit_sha", "pipelines", ["commit_sha"])
    op.create_index("ix_pipelines_status",     "pipelines", ["status"])
    op.create_index("ix_pipelines_created_at", "pipelines", ["created_at"])

    # pipeline_runs
    op.create_table(
        "pipeline_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("pipeline_id",      UUID(as_uuid=True), sa.ForeignKey("pipelines.id"), nullable=False),
        sa.Column("step_name",        sa.String(255), nullable=False),
        sa.Column("status",           sa.String(20),  nullable=False),
        sa.Column("log_url",          sa.Text),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("agent_name",       sa.String(100)),
        sa.Column("metadata",         JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pipeline_runs_pipeline_id", "pipeline_runs", ["pipeline_id"])

    # incidents
    op.create_table(
        "incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("title",               sa.String(512), nullable=False),
        sa.Column("severity",            sa.String(10),  nullable=False),
        sa.Column("status",              sa.String(20),  nullable=False, server_default="open"),
        sa.Column("service",             sa.String(255), nullable=False),
        sa.Column("environment",         sa.String(50),  server_default="production"),
        sa.Column("root_cause_commit",   sa.String(40)),
        sa.Column("root_cause_analysis", sa.Text),
        sa.Column("postmortem_draft",    sa.Text),
        sa.Column("suggested_fix",       sa.Text),
        sa.Column("affected_services",   JSON),
        sa.Column("timeline",            JSON),
        sa.Column("pagerduty_id",        sa.String(100)),
        sa.Column("github_issue_url",    sa.Text),
        sa.Column("slack_thread_url",    sa.Text),
        sa.Column("slack_summary",       sa.Text),
        sa.Column("resolved_at",         sa.String(50)),
        sa.Column("mttr_seconds",        sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_incidents_status",   "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_service",  "incidents", ["service"])

    # quality_gates
    op.create_table(
        "quality_gates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name",               sa.String(255), nullable=False),
        sa.Column("repo_pattern",       sa.String(255), server_default="*"),
        sa.Column("gate_type",          sa.String(50),  nullable=False),
        sa.Column("enabled",            sa.Boolean,     server_default="true"),
        sa.Column("threshold_value",    sa.Float),
        sa.Column("threshold_operator", sa.String(10),  server_default="gte"),
        sa.Column("adaptive_enabled",   sa.Boolean,     server_default="true"),
        sa.Column("adaptive_prompt",    sa.Text),
        sa.Column("context_factors",    JSON),
        sa.Column("description",        sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # agent_tasks
    op.create_table(
        "agent_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("pipeline_id",     UUID(as_uuid=True), sa.ForeignKey("pipelines.id"), nullable=True),
        sa.Column("parent_task_id",  UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id"), nullable=True),
        sa.Column("agent_type",      sa.String(50), nullable=False),
        sa.Column("status",          sa.String(20), nullable=False, server_default="queued"),
        sa.Column("input_payload",   JSON),
        sa.Column("output_payload",  JSON),
        sa.Column("error_detail",    sa.Text),
        sa.Column("execution_trace", JSON),
        sa.Column("tokens_used",     sa.Integer),
        sa.Column("model_used",      sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_tasks_pipeline_id", "agent_tasks", ["pipeline_id"])
    op.create_index("ix_agent_tasks_status",      "agent_tasks", ["status"])


def downgrade() -> None:
    op.drop_table("agent_tasks")
    op.drop_table("quality_gates")
    op.drop_table("incidents")
    op.drop_table("pipeline_runs")
    op.drop_table("pipelines")
