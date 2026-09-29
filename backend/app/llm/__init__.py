"""LLM provider abstraction used by the agent loop.

Messages and content blocks use the Anthropic Messages API shape (the only real provider), so the
Anthropic provider passes them through untouched, and the Agent Core speaks the same structure.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    # Assistant content blocks as returned; appended to the transcript verbatim so thinking and
    # fallback blocks survive across loop iterations.
    content: list[dict[str, Any]]
    stop_reason: str
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(b["text"] for b in self.content if b.get("type") == "text" and b.get("text")).strip()

    @property
    def tool_uses(self) -> list[ToolUse]:
        return [
            ToolUse(id=b["id"], name=b["name"], input=b.get("input") or {})
            for b in self.content
            if b.get("type") == "tool_use"
        ]


class LLMError(Exception):
    """A provider failure. `message` is safe to show to the user."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class LLMProvider(Protocol):
    name: str

    def complete(self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> LLMResponse: ...


@lru_cache
def get_provider() -> LLMProvider:
    settings = get_settings()
    if settings.agent_core_mode in ("http", "agent"):
        from app.llm.agent_core import AgentCoreProvider

        return AgentCoreProvider(settings)
    if settings.llm_configured:
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings)
    return UnconfiguredProvider()


class UnconfiguredProvider:
    """No LLM configured: every call fails with a clear message. There is no fake assistant."""

    name = "unconfigured"

    def complete(self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> LLMResponse:
        raise LLMError(
            "The assistant isn't set up yet. Set AGENT_CORE_MODE=agent (with the Agent Core configured) "
            "or LLM_PROVIDER=anthropic and LLM_API_KEY in backend/.env."
        )
