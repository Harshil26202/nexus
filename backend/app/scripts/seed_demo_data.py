"""Seed rich demo data so the dashboard looks impressive on first launch."""
import asyncio
import random
from datetime import datetime, timedelta, timezone

import structlog

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.agent_task import AgentTask, AgentTaskStatus, AgentType
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.pipeline import Pipeline, PipelineStatus, RiskLevel
from app.models.quality_gate import GateType, QualityGate

log = structlog.get_logger()

REPOS = [
    "acme-corp/payment-service",
    "acme-corp/auth-service",
    "acme-corp/api-gateway",
    "acme-corp/notification-service",
    "acme-corp/user-service",
    "acme-corp/frontend-app",
]

COMMIT_MESSAGES = [
    "feat: add retry logic to payment processor",
    "fix: resolve race condition in session handler",
    "refactor: extract auth middleware to shared lib",
    "feat: implement rate limiting on public endpoints",
    "fix: correct CORS headers for mobile clients",
    "chore: bump dependencies to latest stable",
    "feat: add distributed tracing headers",
    "fix: prevent SQL injection in user search",
    "feat: implement circuit breaker pattern",
    "refactor: migrate from sync to async Redis client",
]

SEMANTIC_SUMMARIES = [
    "Adds retry logic with exponential backoff to the payment processor. Changes touch the core transaction flow and error handling paths. Blast radius is contained to the payment service but affects the retry state machine shared with refund operations.",
    "Resolves a race condition in the session handler where concurrent requests could corrupt session state. The fix introduces a distributed lock via Redis. Low risk but requires Redis to be highly available.",
    "Extracts authentication middleware into a shared library consumed by 4 services. High blast radius — any regression here affects all authenticated endpoints across the platform.",
    "Implements token bucket rate limiting on all public API endpoints. Changes the request path for all unauthenticated users. Risk is medium as the limiter configuration is conservative.",
]

RISK_FACTORS = [
    ["Touches core payment transaction flow", "Missing test coverage for retry edge cases"],
    ["Distributed lock introduces Redis dependency on auth path"],
    ["Affects 4 downstream services via shared library", "DB schema migration included"],
    ["Changes request routing for all users", "No canary mechanism configured"],
]


async def seed_quality_gates(session) -> None:
    log.info("seed.quality_gates")
    gates = [
        QualityGate(
            name="Code Coverage — Production Services",
            repo_pattern="acme-corp/*-service",
            gate_type=GateType.COVERAGE,
            threshold_value=80.0,
            threshold_operator="gte",
            adaptive_enabled=True,
            adaptive_prompt="Tighten to 85% on Friday deploys. Relax to 75% for hotfix branches.",
            description="Minimum test coverage for all production microservices",
        ),
        QualityGate(
            name="Security — No Critical CVEs",
            repo_pattern="*",
            gate_type=GateType.SECURITY,
            threshold_value=0,
            threshold_operator="lte",
            adaptive_enabled=True,
            adaptive_prompt="Block on any HIGH or CRITICAL CVEs for payment-service and auth-service regardless of context.",
            description="Zero critical vulnerabilities in production dependencies",
        ),
        QualityGate(
            name="Performance — API Latency Budget",
            repo_pattern="acme-corp/api-gateway",
            gate_type=GateType.PERFORMANCE,
            threshold_value=50.0,
            threshold_operator="lte",
            adaptive_enabled=True,
            adaptive_prompt="Tighten to 30ms budget during peak traffic windows (9AM-6PM UTC weekdays).",
            description="p95 latency regression must stay under 50ms vs baseline",
        ),
        QualityGate(
            name="Complexity — Cyclomatic Ceiling",
            repo_pattern="acme-corp/*",
            gate_type=GateType.COMPLEXITY,
            threshold_value=15.0,
            threshold_operator="lte",
            adaptive_enabled=False,
            description="No function may exceed cyclomatic complexity of 15",
        ),
        QualityGate(
            name="AI Gate — Auth Change Review",
            repo_pattern="acme-corp/auth-service",
            gate_type=GateType.CUSTOM_AI,
            adaptive_enabled=True,
            adaptive_prompt="Block deployment if the diff touches auth middleware, JWT handling, or session management without a corresponding security-review label on the PR. Also block if changed files include **/secrets/** or **/keys/**.",
            description="AI-enforced security review gate for auth service changes",
        ),
    ]
    for g in gates:
        session.add(g)


async def seed_pipelines(session) -> list[Pipeline]:
    log.info("seed.pipelines")
    pipelines = []
    now = datetime.now(timezone.utc)

    for i in range(60):
        age = timedelta(hours=random.randint(0, 96))
        repo = random.choice(REPOS)
        status = random.choices(
            [PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.RUNNING],
            weights=[75, 20, 5],
        )[0]
        risk_level = random.choices(
            [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL],
            weights=[35, 40, 18, 7],
        )[0]
        risk_score = {
            RiskLevel.LOW: random.uniform(5, 29),
            RiskLevel.MEDIUM: random.uniform(30, 59),
            RiskLevel.HIGH: random.uniform(60, 79),
            RiskLevel.CRITICAL: random.uniform(80, 100),
        }[risk_level]
        summary_idx = i % len(SEMANTIC_SUMMARIES)

        p = Pipeline(
            repo_full_name=repo,
            branch=random.choice(["main", "develop", f"feature/NEXUS-{100 + i}", "hotfix/urgent-fix"]),
            commit_sha="".join(random.choices("0123456789abcdef", k=40)),
            commit_message=COMMIT_MESSAGES[i % len(COMMIT_MESSAGES)],
            author=random.choice(["alice", "bob", "charlie", "diana", "eve"]),
            pr_number=random.randint(100, 999) if random.random() > 0.4 else None,
            status=status,
            risk_level=risk_level,
            risk_score=round(risk_score, 1),
            semantic_summary=SEMANTIC_SUMMARIES[summary_idx],
            blast_radius={
                "services": random.sample(["payment-service", "auth-service", "user-service"], k=random.randint(1, 3)),
                "apis": ["/api/v1/payments", "/api/v1/users"],
                "db_schemas": random.choice([[], ["transactions"], ["users", "sessions"]]),
                "security_surfaces": random.choice([[], ["JWT validation"], ["session cookies"]]),
                "data_pipelines": [],
            },
            selected_tests=[
                {"name": f"test_{repo.split('/')[1]}_{j}", "path": f"tests/test_{j}.py", "priority": j}
                for j in range(random.randint(20, 80))
            ],
            skipped_tests=[
                {"name": f"test_unrelated_{j}", "path": f"tests/unrelated/test_{j}.py", "reason": "Different service"}
                for j in range(random.randint(100, 400))
            ],
            gate_results={
                "overall": "pass" if status == PipelineStatus.SUCCESS else "fail",
                "can_deploy": status == PipelineStatus.SUCCESS,
                "deploy_recommendation": "deploy" if status == PipelineStatus.SUCCESS else "block",
                "gates": [
                    {"name": "Code Coverage", "result": "pass", "measured_value": round(random.uniform(78, 95), 1), "effective_threshold": 80},
                    {"name": "Security Scan", "result": "pass" if status == PipelineStatus.SUCCESS else "fail", "measured_value": 0 if status == PipelineStatus.SUCCESS else 1, "effective_threshold": 0},
                    {"name": "Performance",   "result": "pass", "measured_value": round(random.uniform(10, 45), 1), "effective_threshold": 50},
                ],
                "risk_summary": f"Risk level is {risk_level.value}. " + ("Deployment approved." if status == PipelineStatus.SUCCESS else "Blocked — security gate failed."),
            },
            ai_recommendation=(
                "Safe to deploy. Monitor error rate for 15 minutes post-deploy."
                if status == PipelineStatus.SUCCESS
                else "Deployment blocked. Security scan found a HIGH severity CVE in a direct dependency. Update before proceeding."
            ),
            duration_seconds=random.randint(45, 320),
            created_at=now - age,
            updated_at=now - age + timedelta(seconds=random.randint(45, 320)),
        )
        session.add(p)
        pipelines.append(p)

    return pipelines


async def seed_incidents(session) -> None:
    log.info("seed.incidents")
    now = datetime.now(timezone.utc)
    incidents_data = [
        {
            "title": "Payment service p99 latency > 2s on checkout endpoint",
            "severity": IncidentSeverity.SEV1,
            "status": IncidentStatus.RESOLVED,
            "service": "payment-service",
            "root_cause_commit": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "root_cause_analysis": "A database query introduced in commit a1b2c3d was missing an index on the `created_at` column of the `transactions` table. Under load, this caused full table scans escalating to O(n) query time.",
            "postmortem_draft": "## Summary\n\nThe payment-service experienced elevated latency (p99 > 2s) for 47 minutes on 2026-05-15 due to a missing database index introduced in a recent deployment.\n\n## Impact\n\nApproximately 12% of checkout attempts timed out. Estimated revenue impact: $24,000.\n\n## Timeline\n- 14:03 UTC — Alert fires: p99 > 2s\n- 14:08 UTC — On-call engineer paged\n- 14:15 UTC — NEXUS identifies root commit a1b2c3d\n- 14:28 UTC — Hotfix index migration deployed\n- 14:50 UTC — p99 returns to < 150ms\n\n## Root Cause\n\nMissing index on `transactions.created_at`. The query was efficient in staging (< 10k rows) but catastrophic in production (> 50M rows).\n\n## Action Items\n\n1. Add mandatory index review to quality gates (P1, due: 2026-05-22)\n2. Add query performance tests to CI pipeline (P2, due: 2026-06-01)\n3. Implement production query plan analysis in staging (P2, due: 2026-06-15)",
            "suggested_fix": "ALTER TABLE transactions ADD INDEX idx_created_at (created_at);",
            "slack_summary": "SEV1 resolved: payment-service latency spike caused by missing DB index on transactions.created_at. Root commit: a1b2c3d. Fixed via emergency index migration. MTTR: 47m.",
            "mttr_seconds": 2820,
            "resolved_at": (now - timedelta(hours=2)).isoformat(),
            "affected_services": ["payment-service", "checkout-service", "order-service"],
        },
        {
            "title": "Auth service returning 500 for 8% of login requests",
            "severity": IncidentSeverity.SEV2,
            "status": IncidentStatus.INVESTIGATING,
            "service": "auth-service",
            "root_cause_commit": None,
            "root_cause_analysis": "Elevated 500 errors correlate with a deployment 2 hours ago. Root cause analysis in progress — NEXUS has narrowed the issue to the JWT token refresh path.",
            "slack_summary": "SEV2 active: auth-service 8% 500 error rate on login. Investigation ongoing. NEXUS narrowing root cause.",
            "affected_services": ["auth-service", "api-gateway"],
        },
        {
            "title": "Notification service queue depth > 50k — messages delayed",
            "severity": IncidentSeverity.SEV3,
            "status": IncidentStatus.IDENTIFIED,
            "service": "notification-service",
            "root_cause_commit": "f9e8d7c6b5a4f9e8d7c6b5a4f9e8d7c6b5a4f9e8",
            "root_cause_analysis": "Consumer group lag grew after a misconfigured batch size was deployed. Messages are being consumed but at 1/10th the normal rate.",
            "slack_summary": "SEV3: notification-service queue depth spike. Root cause identified: misconfigured consumer batch_size. Fix deploying.",
            "affected_services": ["notification-service"],
        },
    ]

    for d in incidents_data:
        inc = Incident(
            title=d["title"],
            severity=d["severity"],
            status=d["status"],
            service=d["service"],
            environment="production",
            root_cause_commit=d.get("root_cause_commit"),
            root_cause_analysis=d.get("root_cause_analysis"),
            postmortem_draft=d.get("postmortem_draft"),
            suggested_fix=d.get("suggested_fix"),
            affected_services=d.get("affected_services", []),
            mttr_seconds=d.get("mttr_seconds"),
            resolved_at=d.get("resolved_at"),
        )
        session.add(inc)


async def seed_agent_tasks(session, pipelines: list[Pipeline]) -> None:
    log.info("seed.agent_tasks")
    agent_types = list(AgentType)
    for p in pipelines[:20]:
        for agent_type in [AgentType.SEMANTIC_ANALYZER, AgentType.TEST_INTELLIGENCE, AgentType.QUALITY_GATE]:
            task = AgentTask(
                pipeline_id=p.id,
                agent_type=agent_type,
                status=AgentTaskStatus.COMPLETED if p.status == PipelineStatus.SUCCESS else AgentTaskStatus.FAILED,
                tokens_used=random.randint(800, 4200),
                model_used="gpt-4o",
                execution_trace=[
                    {"step": "input_received",    "timestamp": 1716000000.0, "data": {}},
                    {"step": "analysis_complete", "timestamp": 1716000002.0, "data": {"success": True}},
                ],
            )
            session.add(task)


async def main() -> None:
    log.info("seed.start")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed_quality_gates(session)
        pipelines = await seed_pipelines(session)
        await session.flush()
        await seed_incidents(session)
        await seed_agent_tasks(session, pipelines)
        await session.commit()

    log.info("seed.complete", pipelines=60, incidents=3, gates=5)


if __name__ == "__main__":
    asyncio.run(main())
