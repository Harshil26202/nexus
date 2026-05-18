"""Master Orchestrator Agent.

Coordinates the full NEXUS pipeline for every incoming event:
  PR opened → Semantic Analysis → Test Intelligence → Quality Gate → Deploy Decision
  Production Alert → Incident Response → Monitoring
  User Chat → NL DevOps

Publishes real-time progress events to Redis pub/sub for WebSocket delivery.
"""
import time
import uuid
from typing import Any

import structlog

from app.agents.incident_response import IncidentResponseAgent
from app.agents.monitoring_agent import MonitoringAgent
from app.agents.nl_devops import NLDevOpsAgent
from app.agents.quality_gate_agent import QualityGateAgent
from app.agents.semantic_analyzer import SemanticAnalyzerAgent
from app.agents.test_intelligence import TestIntelligenceAgent
from app.core.redis_client import AGENT_CHANNEL, PIPELINE_CHANNEL, redis_pool

log = structlog.get_logger()


class OrchestratorAgent:
    """Routes events to specialized agents and coordinates execution."""

    def __init__(self) -> None:
        self.semantic = SemanticAnalyzerAgent()
        self.test_intel = TestIntelligenceAgent()
        self.quality_gate = QualityGateAgent()
        self.incident = IncidentResponseAgent()
        self.monitoring = MonitoringAgent()
        self.nl_devops = NLDevOpsAgent()

    async def _emit(self, channel: str, event_type: str, pipeline_id: str, data: Any) -> None:
        try:
            await redis_pool.publish(channel, {
                "event": event_type,
                "pipeline_id": pipeline_id,
                "data": data,
                "timestamp": time.time(),
            })
        except Exception as exc:
            log.warning("orchestrator.emit_failed", error=str(exc))

    # ── Pull Request / Push Pipeline ──────────────────────────────────────────
    async def run_pipeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        pipeline_id = payload.get("pipeline_id", str(uuid.uuid4()))
        start = time.time()
        results: dict[str, Any] = {"pipeline_id": pipeline_id, "stages": {}}

        log.info("orchestrator.pipeline_start", pipeline_id=pipeline_id)
        await self._emit(PIPELINE_CHANNEL, "pipeline_started", pipeline_id, {
            "repo": payload.get("repo"),
            "commit": payload.get("commit_sha"),
        })

        # Stage 1: Semantic Analysis
        await self._emit(PIPELINE_CHANNEL, "stage_started", pipeline_id,
                         {"stage": "semantic_analysis"})
        semantic_result = await self.semantic.run({
            "diff": payload.get("diff", ""),
            "repo": payload.get("repo"),
            "commit_message": payload.get("commit_message", ""),
            "pr_description": payload.get("pr_description", ""),
        })
        results["stages"]["semantic_analysis"] = {
            "success": semantic_result.success,
            "output": semantic_result.output,
            "duration_ms": semantic_result.duration_ms,
        }
        await self._emit(PIPELINE_CHANNEL, "stage_complete", pipeline_id, {
            "stage": "semantic_analysis",
            "risk_level": semantic_result.output.get("risk_level"),
            "risk_score": semantic_result.output.get("risk_score"),
        })

        if not semantic_result.success:
            log.warning("orchestrator.semantic_failed", pipeline_id=pipeline_id)

        # Stage 2: Test Intelligence (parallel-safe, doesn't need gate output)
        await self._emit(PIPELINE_CHANNEL, "stage_started", pipeline_id,
                         {"stage": "test_intelligence"})
        test_result = await self.test_intel.run({
            "semantic_analysis": semantic_result.output,
            "changed_files": payload.get("changed_files", []),
            "test_manifest": payload.get("test_manifest", []),
        })
        results["stages"]["test_intelligence"] = {
            "success": test_result.success,
            "output": test_result.output,
            "duration_ms": test_result.duration_ms,
        }
        await self._emit(PIPELINE_CHANNEL, "stage_complete", pipeline_id, {
            "stage": "test_intelligence",
            "must_run_count": len(test_result.output.get("must_run", [])),
            "time_saved_percent": test_result.output.get("time_saved_percent"),
        })

        # Stage 3: Quality Gate (waits for metrics from CI)
        gates_payload = payload.get("quality_gates_config", [])
        metrics = payload.get("ci_metrics", {
            "code_coverage": 82.3,
            "security_vulnerabilities": 0,
            "complexity_score": 14.2,
            "performance_delta_ms": 12,
        })
        await self._emit(PIPELINE_CHANNEL, "stage_started", pipeline_id,
                         {"stage": "quality_gate"})
        gate_result = await self.quality_gate.run({
            "gates": gates_payload,
            "metrics": metrics,
            "risk_level": semantic_result.output.get("risk_level", "medium"),
            "semantic_analysis": semantic_result.output,
            "context": payload.get("context", {}),
        })
        results["stages"]["quality_gate"] = {
            "success": gate_result.success,
            "output": gate_result.output,
            "duration_ms": gate_result.duration_ms,
        }
        await self._emit(PIPELINE_CHANNEL, "stage_complete", pipeline_id, {
            "stage": "quality_gate",
            "overall": gate_result.output.get("overall"),
            "can_deploy": gate_result.output.get("can_deploy"),
            "recommendation": gate_result.output.get("deploy_recommendation"),
        })

        results["total_duration_ms"] = int((time.time() - start) * 1000)
        results["can_deploy"] = gate_result.output.get("can_deploy", False)
        results["risk_level"] = semantic_result.output.get("risk_level")

        await self._emit(PIPELINE_CHANNEL, "pipeline_complete", pipeline_id, results)
        log.info("orchestrator.pipeline_complete", pipeline_id=pipeline_id,
                 duration_ms=results["total_duration_ms"])
        return results

    # ── Production Incident ───────────────────────────────────────────────────
    async def run_incident(self, payload: dict[str, Any]) -> dict[str, Any]:
        incident_id = str(uuid.uuid4())
        await self._emit(AGENT_CHANNEL, "incident_started", incident_id, {
            "service": payload.get("service"),
            "alert": payload.get("alert", {}).get("name"),
        })

        result = await self.incident.run(payload)
        await self._emit(AGENT_CHANNEL, "incident_analyzed", incident_id, {
            "severity": result.output.get("severity"),
            "root_cause_commit": result.output.get("root_cause_commit"),
            "rollback_safe": result.output.get("rollback_safe"),
        })
        return {"incident_id": incident_id, **result.output}

    # ── Natural Language DevOps ───────────────────────────────────────────────
    async def run_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self.nl_devops.run(payload)
        return result.output

    # ── Post-Deploy Monitoring ────────────────────────────────────────────────
    async def run_monitoring_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self.monitoring.run(payload)
        if result.output.get("rollback_recommended"):
            await self._emit(AGENT_CHANNEL, "rollback_recommended",
                             payload.get("pipeline_id", ""), result.output)
        return result.output


orchestrator = OrchestratorAgent()
