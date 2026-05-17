"""Natural Language DevOps Agent.

Accepts free-text DevOps commands and executes them via tool calls:
  - "Roll back auth-service to last stable"
  - "Show me the risk of deploying this PR"
  - "What changed in the last 3 deploys to production?"
  - "Create an incident for the payment service latency spike"
"""
import json
import time
from typing import Any

from app.agents.base import AgentMessage, AgentResult, BaseAgent

SYSTEM = """
You are NEXUS NL DevOps — an AI that translates natural language into DevOps actions.

You have access to these tools:
- get_pipeline_status(pipeline_id): get current pipeline status
- get_recent_deploys(service, environment, count): list recent deployments
- get_risk_assessment(commit_sha): get AI risk score for a commit
- trigger_rollback(service, target_commit, environment): initiate rollback
- create_incident(title, severity, service): create a new incident
- get_incident_list(status, service): list active incidents
- get_analytics(metric, time_range): pull pipeline/deploy analytics

Parse the user intent, determine what tools to call, execute them, and
respond in natural language with the results.

ALWAYS confirm destructive actions (rollback, redeploy) before executing.
Return JSON with your action plan and response.
""".strip()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_status",
            "description": "Get status of a specific pipeline run",
            "parameters": {
                "type": "object",
                "properties": {
                    "pipeline_id": {"type": "string"},
                },
                "required": ["pipeline_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_deploys",
            "description": "List recent deployments for a service",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "environment": {"type": "string", "enum": ["production", "staging", "dev"]},
                    "count": {"type": "integer", "default": 5},
                },
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_rollback",
            "description": "Trigger a service rollback to a target commit",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "target_commit": {"type": "string"},
                    "environment": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["service", "target_commit", "environment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_incident",
            "description": "Create a new production incident",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["sev1", "sev2", "sev3", "sev4"]},
                    "service": {"type": "string"},
                },
                "required": ["title", "severity", "service"],
            },
        },
    },
]


class NLDevOpsAgent(BaseAgent):
    name = "nl_devops"
    temperature = 0.2
    max_tokens = 2048

    @property
    def system_prompt(self) -> str:
        return SYSTEM

    async def run(self, payload: dict[str, Any]) -> AgentResult:
        trace: list[dict] = []
        start = time.time()

        user_input = payload.get("message", "")
        history = payload.get("history", [])

        self._trace_step(trace, "user_input", {"message": user_input})

        messages = [AgentMessage(role="system", content=SYSTEM)]
        for h in history[-10:]:  # last 10 turns for context
            messages.append(AgentMessage(role=h["role"], content=h["content"]))
        messages.append(AgentMessage(role="user", content=user_input))

        user_msg_for_llm = f"""
User command: {user_input}

Parse the intent and return JSON:
{{
  "intent": "what the user wants",
  "requires_confirmation": false,
  "tools_to_call": [
    {{"tool": "tool_name", "params": {{}}}}
  ],
  "response": "natural language response to the user",
  "follow_up_suggestions": ["suggestion 1", "suggestion 2"]
}}
""".strip()

        messages[-1] = AgentMessage(role="user", content=user_msg_for_llm)

        try:
            raw, tokens = await self._chat(messages, response_format={"type": "json_object"})
            result = json.loads(raw)
            self._trace_step(trace, "intent_parsed", {
                "intent": result.get("intent"),
                "tools": result.get("tools_to_call", []),
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
                output={"response": "I encountered an error processing your request."},
                execution_trace=trace,
                error=str(exc),
                duration_ms=int((time.time() - start) * 1000),
            )
