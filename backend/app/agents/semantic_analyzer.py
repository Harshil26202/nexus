"""Semantic Diff Analyzer Agent.

Reads a raw git diff and produces:
  - A plain-language summary of what changed and why it matters
  - Blast radius: services, APIs, DB schemas, security surfaces touched
  - Risk score (0-100) and level (low/medium/high/critical)
  - Change categories (feature/refactor/bugfix/config/infra/security)
"""
import json
import time
from typing import Any

from app.agents.base import AgentMessage, AgentResult, BaseAgent


SYSTEM = """
You are NEXUS Semantic Analyzer, a senior principal engineer AI.
Your job is to deeply understand git diffs and produce structured intelligence.

When analyzing a diff you MUST:
1. Understand the INTENT behind the changes, not just what lines changed
2. Identify all affected systems, services, APIs, DB schemas, security boundaries
3. Assess blast radius — what could break if this ships
4. Assign a risk score 0-100 and risk level (low/medium/high/critical)
5. Categorize the change (feature/refactor/bugfix/config/infra/security/chore)

Respond ONLY with valid JSON matching the schema in the user message.
""".strip()


class SemanticAnalyzerAgent(BaseAgent):
    name = "semantic_analyzer"
    temperature = 0.0

    @property
    def system_prompt(self) -> str:
        return SYSTEM

    async def run(self, payload: dict[str, Any]) -> AgentResult:
        trace: list[dict] = []
        start = time.time()

        diff = payload.get("diff", "")
        repo = payload.get("repo", "unknown")
        commit_message = payload.get("commit_message", "")
        pr_description = payload.get("pr_description", "")

        self._trace_step(trace, "input_received", {
            "repo": repo,
            "diff_size_bytes": len(diff),
            "commit_message": commit_message,
        })

        user_msg = f"""
Analyze the following git diff for repository: {repo}

Commit message: {commit_message}
PR description: {pr_description}

<diff>
{diff[:12000]}
</diff>

Return JSON with this exact schema:
{{
  "summary": "2-3 sentence plain English summary of what changed",
  "intent": "what problem this change solves or what feature it adds",
  "categories": ["feature|refactor|bugfix|config|infra|security|chore"],
  "blast_radius": {{
    "services": ["list of service names affected"],
    "apis": ["endpoint paths changed or affected"],
    "db_schemas": ["table/collection names modified"],
    "security_surfaces": ["auth, tokens, permissions, encryption areas touched"],
    "data_pipelines": ["any data flows or ETL paths affected"]
  }},
  "risk_score": 0,
  "risk_level": "low|medium|high|critical",
  "risk_factors": ["specific reasons contributing to the risk score"],
  "hidden_risks": ["non-obvious risks a reviewer might miss"],
  "estimated_test_coverage_needed": ["areas that MUST have test coverage"],
  "deploy_considerations": ["Friday deploy? DB migration? Feature flag needed?"]
}}
""".strip()

        messages = [
            AgentMessage(role="system", content=SYSTEM),
            AgentMessage(role="user", content=user_msg),
        ]

        try:
            raw, tokens = await self._chat(messages, response_format={"type": "json_object"})
            result = json.loads(raw)
            self._trace_step(trace, "analysis_complete", result)

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
                duration_ms=int((time.time() - start) * 1000),
                error=str(exc),
            )
