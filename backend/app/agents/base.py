"""Base agent class with shared Azure AI Foundry integration, tracing, and retry logic."""
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog
from opentelemetry import trace
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.azure_clients import get_openai_client
from app.core.config import settings
from app.core.telemetry import get_tracer

log = structlog.get_logger()
tracer = get_tracer("nexus.agents")


@dataclass
class AgentMessage:
    role: str  # system | user | assistant | tool
    content: str
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    output: dict[str, Any]
    execution_trace: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: int = 0
    error: str | None = None


class BaseAgent(ABC):
    name: str = "base"
    model: str = settings.AZURE_OPENAI_DEPLOYMENT
    temperature: float = 0.1
    max_tokens: int = 4096

    def __init__(self) -> None:
        self._client = get_openai_client()
        self._log = log.bind(agent=self.name)

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    async def run(self, payload: dict[str, Any]) -> AgentResult: ...

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ) -> tuple[str, int]:
        openai_msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_msgs,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if response_format:
            kwargs["response_format"] = response_format

        with tracer.start_as_current_span(f"agent.{self.name}.chat") as span:
            span.set_attribute("agent.name", self.name)
            resp = await self._client.chat.completions.create(**kwargs)
            tokens = resp.usage.total_tokens if resp.usage else 0
            span.set_attribute("llm.tokens", tokens)
            content = resp.choices[0].message.content or ""
            return content, tokens

    def _trace_step(self, trace_list: list, step: str, data: Any) -> None:
        trace_list.append({
            "step": step,
            "timestamp": time.time(),
            "data": data,
        })
