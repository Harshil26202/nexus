"""Dynamic Quality Gate Agent.

Evaluates configured gates against pipeline metrics, adapting thresholds
based on context (risk level, deploy time, environment, change size).
"""
import json
import time
from datetime import datetime, timezone
from typing import Any

from app.agents.base import AgentMessage, AgentResult, BaseAgent

SYSTEM = """
You are NEXUS Quality Gate AI, responsible for making go/no-go decisions on deployments.

You adapt gate thresholds based on context — a Friday 5PM deploy to production gets
tighter gates than a Thursday morning deploy to staging. A large risky diff gets
stricter coverage requirements than a typo fix.

You must be fair, consistent, and explain your reasoning clearly.
For each gate you MUST provide: pass/fail, effective threshold used, reasoning.

Respond ONLY with valid JSON.
""".strip()


class QualityGateAgent(BaseAgent):
    name = "quality_gate"
    temperature = 0.0
    model_override: str | None = None  # Use mini model for speed

    @property
    def system_prompt(self) -> str:
        return SYSTEM

    async def run(self, payload: dict[str, Any]) -> AgentResult:
        trace: list[dict] = []
        start = time.time()

        gates = payload.get("gates", [])
        metrics = payload.get("metrics", {})
        context = payload.get("context", {})
        risk_level = payload.get("risk_level", "medium")
        analysis = payload.get("semantic_analysis", {})

        now = datetime.now(timezone.utc)
        deploy_context = {
            "day_of_week": now.strftime("%A"),
            "hour_utc": now.hour,
            "is_friday": now.weekday() == 4,
            "is_after_3pm_utc": now.hour >= 15,
            "risk_level": risk_level,
            "environment": context.get("environment", "production"),
        }

        self._trace_step(trace, "context_built", deploy_context)

        user_msg = f"""
Deploy Context:
{json.dumps(deploy_context, indent=2)}

Semantic Analysis Summary:
Risk Score: {analysis.get("risk_score", 50)}
Categories: {analysis.get("categories", [])}
Blast Radius: {analysis.get("blast_radius", {})}

Configured Quality Gates:
{json.dumps(gates, indent=2)}

Measured Metrics:
{json.dumps(metrics, indent=2)}

Evaluate each gate and return JSON:
{{
  "overall": "pass|fail|warn",
  "can_deploy": true,
  "deploy_recommendation": "deploy|block|deploy_with_monitoring|delay_to_morning",
  "gates": [
    {{
      "name": "gate name",
      "type": "coverage|security|performance|complexity|custom_ai",
      "result": "pass|fail|warn",
      "measured_value": 0,
      "effective_threshold": 0,
      "baseline_threshold": 0,
      "threshold_adjusted": true,
      "adjustment_reason": "why threshold was tightened/relaxed",
      "reasoning": "full explanation"
    }}
  ],
  "risk_summary": "plain English summary of overall deploy risk",
  "monitoring_recommendations": ["what to watch after deploy"]
}}
""".strip()

        messages = [
            AgentMessage(role="system", content=SYSTEM),
            AgentMessage(role="user", content=user_msg),
        ]

        try:
            raw, tokens = await self._chat(messages, response_format={"type": "json_object"})
            result = json.loads(raw)
            self._trace_step(trace, "gates_evaluated", {
                "overall": result.get("overall"),
                "can_deploy": result.get("can_deploy"),
                "gates_failed": [
                    g["name"] for g in result.get("gates", []) if g.get("result") == "fail"
                ],
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
                output={"overall": "fail", "can_deploy": False},
                execution_trace=trace,
                error=str(exc),
                duration_ms=int((time.time() - start) * 1000),
            )
