"""Central tool registry.

A tool is the only way the agent can act. Each one declares a name, description, Pydantic input
and output schemas, a risk level (which drives approvals), the permission scope it needs, and an
async handler that talks to the backend through `BackendClient` - never to a database.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from app.backend.client import BackendClient
from app.backend.exceptions import (
    BackendAuthError,
    BackendError,
    BackendNotFoundError,
    BackendValidationError,
)
from app.llm.base import LLMToolSpec
from app.schemas.agent import UserContext
from app.schemas.tool import ToolDomain, ToolInput, ToolRisk

if TYPE_CHECKING:
    from app.memory.long_term import LongTermMemory

logger = logging.getLogger(__name__)

ALL_SCOPES = frozenset({f"{d.value}:{a}" for d in ToolDomain for a in ("read", "write")})


class ToolError(Exception):
    """A tool failure whose message is safe to return to the model and the user."""


class ToolInputError(ToolError):
    pass


class ToolPermissionError(ToolError):
    pass


@dataclass
class ToolContext:
    backend: BackendClient
    user: UserContext
    today: date
    memory: "LongTermMemory | None" = None
    scopes: frozenset[str] = ALL_SCOPES


# Handlers return a Pydantic model: a backend entity (Task, Bill, ...) or a ToolOutput.
Handler = Callable[[ToolContext, Any], Awaitable[BaseModel]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    domain: ToolDomain
    risk: ToolRisk
    input_model: type[ToolInput]
    output_model: type[BaseModel]
    handler: Handler
    # Human-readable reason shown on the approval card when this tool needs approval.
    approval_reason: str = "This action changes your data."
    examples: tuple[str, ...] = field(default_factory=tuple)

    @property
    def permission(self) -> str:
        return f"{self.domain.value}:{'read' if self.risk == ToolRisk.READ else 'write'}"

    def spec(self) -> LLMToolSpec:
        schema = self.input_model.model_json_schema(by_alias=False)
        schema.pop("title", None)
        for prop in schema.get("properties", {}).values():
            prop.pop("title", None)
        return LLMToolSpec(self.name, self.description, schema)

    def requires_approval(self, mutation_policy: str) -> bool:
        if self.risk == ToolRisk.CONSEQUENTIAL:
            return True
        return self.risk == ToolRisk.MUTATE and mutation_policy == "approval"

    def parse(self, raw: dict[str, Any] | None) -> ToolInput:
        try:
            return self.input_model.model_validate(raw or {})
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'input'}: {e['msg']}" for e in exc.errors())
            raise ToolInputError(f"Invalid input for {self.name}: {problems}")


class ToolRegistry:
    def __init__(self, tool_timeout_seconds: float = 20.0) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self.tool_timeout_seconds = tool_timeout_seconds

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def register_all(self, tools: Iterable[ToolDefinition]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def tools(self, domains: Iterable[ToolDomain] | None = None) -> list[ToolDefinition]:
        if domains is None:
            return list(self._tools.values())
        wanted = set(domains)
        return [t for t in self._tools.values() if t.domain in wanted]

    def specs(self, domains: Iterable[ToolDomain] | None = None) -> list[LLMToolSpec]:
        return [t.spec() for t in self.tools(domains)]

    async def execute(self, tool: ToolDefinition, args: ToolInput, ctx: ToolContext) -> dict[str, Any]:
        """Run a validated call. Raises ToolError with a safe message on any failure."""
        if tool.permission not in ctx.scopes:
            raise ToolPermissionError(f"The assistant isn't allowed to use {tool.name}.")
        try:
            result = await asyncio.wait_for(tool.handler(ctx, args), timeout=self.tool_timeout_seconds)
        except TimeoutError:
            raise ToolError(f"{tool.name} timed out.")
        except BackendValidationError as exc:
            raise ToolError(f"The request was rejected: {exc.message}")
        except BackendNotFoundError:
            raise ToolError("That item was not found.")
        except BackendAuthError:
            raise ToolError("Not authorized to access that data.")
        except BackendError as exc:
            raise ToolError(exc.message)
        output = tool.output_model.model_validate(result.model_dump() if isinstance(result, BaseModel) else result)
        return output.model_dump(mode="json", exclude_none=True)

    def as_langchain_tools(self, ctx: ToolContext, domains: Iterable[ToolDomain] | None = None) -> list[Any]:
        """Expose read-only tools as LangChain `StructuredTool`s (for chains or evaluation harnesses).

        Mutating tools are deliberately excluded: they must go through the agent graph so the
        approval policy applies.
        """
        from langchain_core.tools import StructuredTool

        def make(tool: ToolDefinition) -> StructuredTool:
            async def _run(**kwargs: Any) -> dict[str, Any]:
                return await self.execute(tool, tool.parse(kwargs), ctx)

            return StructuredTool.from_function(
                coroutine=_run, name=tool.name, description=tool.description, args_schema=tool.input_model
            )

        return [make(t) for t in self.tools(domains) if t.risk == ToolRisk.READ]


def build_default_registry(tool_timeout_seconds: float = 20.0) -> ToolRegistry:
    from app.tools import (
        document_tools,
        event_tools,
        finance_tools,
        goal_tools,
        memory_tools,
        reminder_tools,
        study_tools,
        task_tools,
    )

    registry = ToolRegistry(tool_timeout_seconds)
    for module in (task_tools, event_tools, reminder_tools, study_tools, finance_tools, goal_tools, document_tools, memory_tools):
        registry.register_all(module.TOOLS)
    return registry
