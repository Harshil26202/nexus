"""Test Intelligence Agent.

Given a semantic analysis + full test manifest, determines:
  - Which tests to run (HIGH priority)
  - Which tests to skip (LOW signal given this diff)
  - Which NEW tests to generate
  - Estimated CI time savings vs running all tests
"""
import json
import time
from typing import Any

from app.agents.base import AgentMessage, AgentResult, BaseAgent

SYSTEM = """
You are NEXUS Test Intelligence, an AI that optimizes CI pipelines.
You receive a semantic diff analysis and a test manifest and make intelligent decisions
about which tests to run to maximize signal-to-noise while minimizing CI time.

Principles:
- Prefer false negatives (run more tests when uncertain) over false positives
- Always run tests for directly touched files/modules
- Use dependency graph reasoning to select transitively affected tests
- Skip tests that are provably unaffected (different service, no shared deps)
- Flag tests that should be generated but don't exist yet

Respond ONLY with valid JSON.
""".strip()


class TestIntelligenceAgent(BaseAgent):
    name = "test_intelligence"
    temperature = 0.0

    @property
    def system_prompt(self) -> str:
        return SYSTEM

    async def run(self, payload: dict[str, Any]) -> AgentResult:
        trace: list[dict] = []
        start = time.time()

        analysis = payload.get("semantic_analysis", {})
        test_manifest = payload.get("test_manifest", [])
        changed_files = payload.get("changed_files", [])

        self._trace_step(trace, "input", {
            "changed_files_count": len(changed_files),
            "total_tests": len(test_manifest),
            "risk_level": analysis.get("risk_level"),
        })

        user_msg = f"""
Semantic Analysis:
{json.dumps(analysis, indent=2)}

Changed Files:
{json.dumps(changed_files, indent=2)}

Full Test Manifest (name, path, tags, avg_duration_ms):
{json.dumps(test_manifest[:200], indent=2)}

Return JSON:
{{
  "must_run": [
    {{"name": "test name", "path": "path/to/test", "reason": "why it must run", "priority": 1}}
  ],
  "should_run": [
    {{"name": "test name", "path": "path/to/test", "reason": "transitively affected"}}
  ],
  "skip": [
    {{"name": "test name", "path": "path/to/test", "reason": "unaffected — different service"}}
  ],
  "generate_needed": [
    {{"description": "test that should exist but doesn't", "module": "module path", "scenario": "what to test"}}
  ],
  "estimated_duration_ms_selected": 0,
  "estimated_duration_ms_full": 0,
  "time_saved_percent": 0,
  "confidence": "high|medium|low",
  "reasoning": "brief explanation of selection strategy"
}}
""".strip()

        messages = [
            AgentMessage(role="system", content=SYSTEM),
            AgentMessage(role="user", content=user_msg),
        ]

        try:
            raw, tokens = await self._chat(messages, response_format={"type": "json_object"})
            result = json.loads(raw)
            self._trace_step(trace, "selection_complete", {
                "must_run": len(result.get("must_run", [])),
                "skip": len(result.get("skip", [])),
                "time_saved_percent": result.get("time_saved_percent"),
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
