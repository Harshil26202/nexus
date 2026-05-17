"""Incident Response Agent.

On production alert:
  1. Traces incident back to the root commit using git history + metrics
  2. Identifies affected blast radius
  3. Generates postmortem draft (Google SRE format)
  4. Proposes a code-level fix
  5. Creates GitHub issue + Slack alert
"""
import json
import time
from typing import Any

from app.agents.base import AgentMessage, AgentResult, BaseAgent

SYSTEM = """
You are NEXUS Incident Response AI — a senior SRE with deep expertise in
root cause analysis, incident management, and production systems.

When an incident fires, you:
1. Correlate alert signals with recent deployments
2. Perform 5-Why root cause analysis
3. Draft a Google SRE-style postmortem
4. Propose a minimal code fix
5. Write a concise Slack incident summary

Be precise, calm, and data-driven. Avoid speculation — mark uncertainties clearly.
Respond ONLY with valid JSON.
""".strip()


class IncidentResponseAgent(BaseAgent):
    name = "incident_response"
    temperature = 0.1
    max_tokens = 8192

    @property
    def system_prompt(self) -> str:
        return SYSTEM

    async def run(self, payload: dict[str, Any]) -> AgentResult:
        trace: list[dict] = []
        start = time.time()

        alert = payload.get("alert", {})
        recent_deploys = payload.get("recent_deploys", [])
        error_logs = payload.get("error_logs", "")
        metrics_anomalies = payload.get("metrics_anomalies", {})
        service = payload.get("service", "unknown-service")

        self._trace_step(trace, "incident_received", {
            "service": service,
            "alert_name": alert.get("name"),
            "recent_deploys_count": len(recent_deploys),
        })

        user_msg = f"""
PRODUCTION INCIDENT
Service: {service}
Alert: {json.dumps(alert, indent=2)}

Recent Deployments (last 24h):
{json.dumps(recent_deploys, indent=2)}

Error Logs (last 100 lines):
{error_logs[:3000]}

Metrics Anomalies:
{json.dumps(metrics_anomalies, indent=2)}

Perform incident analysis and return JSON:
{{
  "incident_title": "concise title",
  "severity": "sev1|sev2|sev3|sev4",
  "root_cause_commit": "git SHA if identified, else null",
  "root_cause_summary": "1-2 sentence root cause",
  "five_whys": [
    {{"why": "question", "because": "answer"}}
  ],
  "affected_services": ["service names"],
  "estimated_user_impact": "% of users affected and how",
  "immediate_actions": [
    {{"action": "what to do NOW", "owner": "team/role", "priority": 1}}
  ],
  "rollback_commit": "sha to roll back to if applicable",
  "rollback_safe": true,
  "suggested_fix": {{
    "description": "what code change to make",
    "files_to_change": ["file paths"],
    "patch_description": "pseudocode or description of the fix"
  }},
  "postmortem_draft": {{
    "summary": "executive summary",
    "impact": "user and business impact",
    "timeline": [
      {{"time": "HH:MM UTC", "event": "what happened"}}
    ],
    "root_cause": "detailed technical root cause",
    "contributing_factors": ["list"],
    "detection": "how and when we detected it",
    "resolution": "what resolved it",
    "action_items": [
      {{"item": "what to do", "owner": "team", "due": "timeframe", "priority": "P1|P2|P3"}}
    ],
    "lessons_learned": ["key takeaways"]
  }},
  "slack_summary": "2-3 sentence Slack message for #incidents channel"
}}
""".strip()

        messages = [
            AgentMessage(role="system", content=SYSTEM),
            AgentMessage(role="user", content=user_msg),
        ]

        try:
            raw, tokens = await self._chat(messages, response_format={"type": "json_object"})
            result = json.loads(raw)
            self._trace_step(trace, "analysis_complete", {
                "severity": result.get("severity"),
                "root_cause_commit": result.get("root_cause_commit"),
                "rollback_safe": result.get("rollback_safe"),
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
                output={},
                execution_trace=trace,
                error=str(exc),
                duration_ms=int((time.time() - start) * 1000),
            )
