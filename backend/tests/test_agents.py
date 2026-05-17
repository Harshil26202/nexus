"""Tests for AI agents — mock Azure OpenAI, test input/output contracts."""
import json
import pytest

from app.agents.semantic_analyzer import SemanticAnalyzerAgent
from app.agents.test_intelligence import TestIntelligenceAgent
from app.agents.quality_gate_agent import QualityGateAgent
from app.agents.incident_response import IncidentResponseAgent


SAMPLE_DIFF = """
diff --git a/app/payments/processor.py b/app/payments/processor.py
index a1b2c3d..e4f5g6h 100644
--- a/app/payments/processor.py
+++ b/app/payments/processor.py
@@ -45,6 +45,12 @@ class PaymentProcessor:
+    async def retry_payment(self, payment_id: str, max_retries: int = 3) -> PaymentResult:
+        for attempt in range(max_retries):
+            result = await self._process(payment_id)
+            if result.success:
+                return result
+        raise PaymentRetryExhausted(payment_id)
"""

SAMPLE_ANALYSIS = {
    "summary": "Adds retry logic to payment processor.",
    "risk_score": 45,
    "risk_level": "medium",
    "categories": ["feature"],
    "blast_radius": {
        "services": ["payment-service"],
        "apis": ["/api/v1/payments"],
        "db_schemas": [],
        "security_surfaces": [],
        "data_pipelines": [],
    },
    "risk_factors": ["Retry logic may cause duplicate charges"],
    "hidden_risks": ["No idempotency key used in retry"],
    "estimated_test_coverage_needed": ["retry exhaustion", "idempotency"],
    "deploy_considerations": [],
}

SAMPLE_TEST_MANIFEST = [
    {"name": f"test_payment_{i}", "path": f"tests/payment/test_{i}.py", "tags": ["payment", "unit"], "avg_duration_ms": 200}
    for i in range(30)
] + [
    {"name": f"test_unrelated_{i}", "path": f"tests/other/test_{i}.py", "tags": ["unrelated"], "avg_duration_ms": 100}
    for i in range(50)
]


@pytest.mark.asyncio
async def test_semantic_analyzer_returns_structured_output(mock_openai):
    agent = SemanticAnalyzerAgent()
    result = await agent.run({
        "diff": SAMPLE_DIFF,
        "repo": "acme/payment-service",
        "commit_message": "feat: add retry logic",
        "pr_description": "",
    })
    assert result.success
    assert "summary" in result.output
    assert "risk_score" in result.output
    assert "risk_level" in result.output
    assert result.tokens_used > 0
    assert len(result.execution_trace) >= 2


@pytest.mark.asyncio
async def test_semantic_analyzer_builds_execution_trace(mock_openai):
    agent = SemanticAnalyzerAgent()
    result = await agent.run({
        "diff": SAMPLE_DIFF,
        "repo": "acme/payment-service",
        "commit_message": "test commit",
        "pr_description": "",
    })
    steps = [t["step"] for t in result.execution_trace]
    assert "input_received" in steps
    assert "analysis_complete" in steps


@pytest.mark.asyncio
async def test_test_intelligence_selects_relevant_tests(mock_openai):
    # Override mock with test intelligence response
    import json
    choice = mock_openai.chat.completions.create.return_value.choices[0]
    choice.message.content = json.dumps({
        "must_run": [{"name": "test_payment_0", "path": "tests/payment/test_0.py", "reason": "Directly affected"}],
        "should_run": [],
        "skip": [{"name": "test_unrelated_0", "path": "tests/other/test_0.py", "reason": "Different service"}],
        "generate_needed": [],
        "estimated_duration_ms_selected": 2000,
        "estimated_duration_ms_full": 10000,
        "time_saved_percent": 80,
        "confidence": "high",
        "reasoning": "Only payment tests are affected",
    })

    agent = TestIntelligenceAgent()
    result = await agent.run({
        "semantic_analysis": SAMPLE_ANALYSIS,
        "changed_files": ["app/payments/processor.py"],
        "test_manifest": SAMPLE_TEST_MANIFEST,
    })
    assert result.success
    assert "must_run" in result.output
    assert "time_saved_percent" in result.output


@pytest.mark.asyncio
async def test_quality_gate_pass_scenario(mock_openai):
    import json
    choice = mock_openai.chat.completions.create.return_value.choices[0]
    choice.message.content = json.dumps({
        "overall": "pass",
        "can_deploy": True,
        "deploy_recommendation": "deploy",
        "gates": [
            {"name": "Coverage", "type": "coverage", "result": "pass", "measured_value": 85,
             "effective_threshold": 80, "baseline_threshold": 80, "threshold_adjusted": False,
             "adjustment_reason": "", "reasoning": "Coverage above threshold"},
        ],
        "risk_summary": "All gates pass. Safe to deploy.",
        "monitoring_recommendations": ["Watch error rate for 15m"],
    })

    agent = QualityGateAgent()
    result = await agent.run({
        "gates": [{"name": "Coverage", "type": "coverage", "threshold_value": 80}],
        "metrics": {"code_coverage": 85, "security_vulnerabilities": 0},
        "risk_level": "medium",
        "semantic_analysis": SAMPLE_ANALYSIS,
        "context": {},
    })
    assert result.success
    assert result.output["can_deploy"] is True
    assert result.output["overall"] == "pass"


@pytest.mark.asyncio
async def test_quality_gate_fail_on_high_risk_friday(mock_openai):
    import json
    choice = mock_openai.chat.completions.create.return_value.choices[0]
    choice.message.content = json.dumps({
        "overall": "fail",
        "can_deploy": False,
        "deploy_recommendation": "delay_to_morning",
        "gates": [
            {"name": "Coverage", "type": "coverage", "result": "fail", "measured_value": 78,
             "effective_threshold": 88, "baseline_threshold": 80, "threshold_adjusted": True,
             "adjustment_reason": "Friday deploy + high risk diff — threshold tightened to 88%",
             "reasoning": "Coverage below adjusted Friday threshold"},
        ],
        "risk_summary": "Blocked. Friday + high risk — delay to Monday morning.",
        "monitoring_recommendations": [],
    })

    agent = QualityGateAgent()
    result = await agent.run({
        "gates": [{"name": "Coverage", "type": "coverage", "threshold_value": 80}],
        "metrics": {"code_coverage": 78},
        "risk_level": "high",
        "semantic_analysis": {**SAMPLE_ANALYSIS, "risk_score": 75, "risk_level": "high"},
        "context": {},
    })
    assert result.success
    assert result.output["can_deploy"] is False
    assert result.output["gates"][0]["threshold_adjusted"] is True


@pytest.mark.asyncio
async def test_incident_response_generates_postmortem(mock_openai):
    import json
    choice = mock_openai.chat.completions.create.return_value.choices[0]
    choice.message.content = json.dumps({
        "incident_title": "Payment service p99 > 2s",
        "severity": "sev1",
        "root_cause_commit": "abc1234",
        "root_cause_summary": "Missing DB index on transactions.created_at",
        "five_whys": [
            {"why": "Why was latency high?", "because": "Full table scan on transactions"},
            {"why": "Why full table scan?", "because": "Missing index on created_at"},
        ],
        "affected_services": ["payment-service"],
        "estimated_user_impact": "12% of checkout attempts timed out",
        "immediate_actions": [{"action": "Add index", "owner": "DBA", "priority": 1}],
        "rollback_commit": "def5678",
        "rollback_safe": True,
        "suggested_fix": {"description": "Add index", "files_to_change": ["migrations/"], "patch_description": "CREATE INDEX ..."},
        "postmortem_draft": {"summary": "Latency incident", "impact": "12% timeout", "timeline": [], "root_cause": "Missing index", "contributing_factors": [], "detection": "Alert", "resolution": "Index added", "action_items": [], "lessons_learned": []},
        "slack_summary": "SEV1 resolved: missing DB index. MTTR 47m.",
    })

    agent = IncidentResponseAgent()
    result = await agent.run({
        "alert": {"name": "p99 latency > 2s"},
        "service": "payment-service",
        "recent_deploys": [{"sha": "abc1234", "service": "payment-service"}],
        "error_logs": "ERROR: query timeout",
        "metrics_anomalies": {"p99_latency_ms": 2100},
    })
    assert result.success
    assert result.output["root_cause_commit"] == "abc1234"
    assert result.output["rollback_safe"] is True
    assert "postmortem_draft" in result.output
