"""Monitoring Agent.

Continuously watches deployment health post-deploy:
  - Compares error rate, latency, throughput vs baseline (pre-deploy)
  - Detects anomalies using statistical thresholds
  - Fires auto-rollback triggers if configured
  - Summarizes deployment health in real-time
"""
import json
import time
from typing import Any

from app.agents.base import AgentMessage, AgentResult, BaseAgent

SYSTEM = """
You are NEXUS Monitoring AI, a post-deployment health analyzer.
You compare pre-deploy and post-deploy metrics to detect regressions.

You watch for:
- Error rate spikes (>2x baseline = warn, >5x = critical)
- Latency regressions (p50/p95/p99 increases >20%/50%/100%)
- Throughput drops (>30% drop = investigate)
- Memory/CPU anomalies
- Downstream service degradation

You make auto-rollback recommendations when thresholds are breached.
Respond ONLY with valid JSON.
""".strip()


class MonitoringAgent(BaseAgent):
    name = "monitoring"
    temperature = 0.0

    @property
    def system_prompt(self) -> str:
        return SYSTEM

    async def run(self, payload: dict[str, Any]) -> AgentResult:
        trace: list[dict] = []
        start = time.time()

        pre_metrics = payload.get("pre_deploy_metrics", {})
        post_metrics = payload.get("post_deploy_metrics", {})
        deploy_info = payload.get("deploy_info", {})
        auto_rollback_enabled = payload.get("auto_rollback_enabled", False)

        self._trace_step(trace, "metrics_received", {
            "service": deploy_info.get("service"),
            "commit": deploy_info.get("commit_sha"),
        })

        user_msg = f"""
Deployment Info:
{json.dumps(deploy_info, indent=2)}

Pre-Deploy Metrics (baseline):
{json.dumps(pre_metrics, indent=2)}

Post-Deploy Metrics (current):
{json.dumps(post_metrics, indent=2)}

Auto-rollback enabled: {auto_rollback_enabled}

Analyze and return JSON:
{{
  "health_status": "healthy|degraded|critical",
  "overall_score": 0,
  "metrics_analysis": [
    {{
      "metric": "error_rate",
      "baseline": 0,
      "current": 0,
      "change_pct": 0,
      "status": "ok|warn|critical",
      "explanation": "what this means"
    }}
  ],
  "anomalies_detected": [
    {{"metric": "name", "severity": "warn|critical", "description": "what happened"}}
  ],
  "rollback_recommended": false,
  "rollback_urgency": "immediate|within_15min|monitor|none",
  "rollback_reason": "reason if recommended",
  "deployment_verdict": "success|partial|failed",
  "monitoring_window_complete": false,
  "next_check_seconds": 60,
  "summary": "plain English health summary"
}}
""".strip()

        messages = [
            AgentMessage(role="system", content=SYSTEM),
            AgentMessage(role="user", content=user_msg),
        ]

        try:
            raw, tokens = await self._chat(messages, response_format={"type": "json_object"})
            result = json.loads(raw)
            self._trace_step(trace, "health_assessed", {
                "status": result.get("health_status"),
                "rollback_recommended": result.get("rollback_recommended"),
            })
            return AgentResult(
                agent_name=self.name,
                success=True,
                output=result,
                execution_trace=trace,
                tokens_used=tokens,
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as exc:
            self._trace_step(trace, "error", str(exc))
            return AgentResult(
                agent_name=self.name,
                success=False,
                output={"health_status": "unknown"},
                execution_trace=trace,
                error=str(exc),
                duration_ms=int((time.time() - start) * 1000),
            )
