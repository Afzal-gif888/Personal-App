"""Provider-neutral LLM interface.

Transcripts use the Messages API content-block shape (`{"role", "content": [blocks]}` with `text`,
`tool_use` and `tool_result` blocks). It is the richest common format for tool calling, and the
backend already speaks it, so providers translate to/from it at their edge.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from app.schemas.tool import ToolCallRequest

Purpose = Literal["act", "plan"]


@dataclass(frozen=True)
class LLMToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class LLMResult:
    # Assistant content blocks, appended to the transcript verbatim (thinking blocks included) so
    # multi-turn tool use stays valid for providers that require it.
    content: list[dict[str, Any]]
    stop_reason: str = "end_turn"
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(b["text"] for b in self.content if b.get("type") == "text" and b.get("text")).strip()

    @property
    def tool_calls(self) -> list[ToolCallRequest]:
        return [
            ToolCallRequest(id=b["id"], name=b["name"], input=b.get("input") or {})
            for b in self.content
            if b.get("type") == "tool_use"
        ]


class LLMError(Exception):
    """A provider failure. `message` is safe to show to the user."""

    def __init__(self, message: str, *, retryable: bool = False, rate_limited: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.rate_limited = rate_limited


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    async def invoke(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[LLMToolSpec],
        purpose: Purpose = "act",
    ) -> LLMResult:
        """One model turn. `purpose="plan"` is a tool-free planning call."""

    async def aclose(self) -> None:  # pragma: no cover - optional hook
        return None


class UnconfiguredLLMProvider(LLMProvider):
    """Used when no API key is set. Every call fails with a clear message; there is no fake assistant."""

    name = "unconfigured"
    model = ""

    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def invoke(self, *, system, messages, tools, purpose: Purpose = "act") -> LLMResult:
        raise LLMError(
            f"The assistant isn't set up yet: add an API key for '{self.provider}' as LLM_API_KEY in agent-core/.env."
        )
