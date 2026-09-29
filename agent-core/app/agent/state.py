"""Typed, serializable agent state.

Everything here is plain data (Pydantic models, strings, numbers, lists and dicts) so a run can be
checkpointed or inspected. Services such as the LLM or backend client are *not* state; they are
passed to nodes through the run config (see `nodes.RunDeps`).

List fields annotated with `operator.add` are append-only: a node returns only its new items.
"""

import operator
from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.rag.schemas import RetrievedChunk
from app.schemas.agent import (
    AgentError,
    ApprovalRequest,
    Intent,
    Observation,
    RunStatus,
    UserContext,
)
from app.schemas.events import AgentEvent
from app.schemas.memory import ConversationTurn
from app.schemas.tool import ToolCallRecord, ToolCallRequest


class ContextSnapshot(BaseModel):
    """Relevant, bounded context for this request - never the whole database."""

    local_now: str = ""  # ISO timestamp in the user's timezone
    today: str = ""  # YYYY-MM-DD in the user's timezone
    facts: dict[str, Any] = Field(default_factory=dict)  # long-term memory
    highlights: dict[str, list[str]] = Field(default_factory=dict)  # domain -> short lines


class AgentState(BaseModel):
    run_id: str
    request: str
    conversation_id: str | None = None
    expected_user_id: str | None = None
    history: list[ConversationTurn] | None = None  # prior turns sent by the backend, if any

    user: UserContext | None = None
    context: ContextSnapshot = Field(default_factory=ContextSnapshot)
    intent: Intent = Field(default_factory=Intent)
    plan: list[str] = Field(default_factory=list)

    # Messages API transcript: prior turns + this request + assistant/tool turns.
    messages: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)
    pending_tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    tool_calls: Annotated[list[ToolCallRecord], operator.add] = Field(default_factory=list)
    observations: Annotated[list[Observation], operator.add] = Field(default_factory=list)
    pending_approvals: Annotated[list[ApprovalRequest], operator.add] = Field(default_factory=list)
    retrieved_documents: Annotated[list[RetrievedChunk], operator.add] = Field(default_factory=list)
    events: Annotated[list[AgentEvent], operator.add] = Field(default_factory=list)

    iterations: int = 0
    tool_call_count: int = 0
    stop_reason: str | None = None  # why the loop ended early: "iteration_limit", "tool_limit", "refusal"

    final_response: str | None = None
    status: RunStatus | None = None
    error: AgentError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
