"""Structured run events. The backend relays these to the frontend; the frontend never generates them."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentEventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"
    CONTEXT_LOADED = "CONTEXT_LOADED"
    REQUEST_UNDERSTOOD = "REQUEST_UNDERSTOOD"
    DOCUMENTS_RETRIEVED = "DOCUMENTS_RETRIEVED"
    PLANNING_STARTED = "PLANNING_STARTED"
    PLAN_CREATED = "PLAN_CREATED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    LIMIT_REACHED = "LIMIT_REACHED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"


def _now() -> datetime:
    return datetime.now(UTC)


class AgentEvent(BaseModel):
    type: AgentEventType
    run_id: str
    timestamp: datetime = Field(default_factory=_now)
    # Safe, user-facing metadata only (tool names, counts, statuses) - never prompts or reasoning.
    data: dict[str, Any] = Field(default_factory=dict)


def event(type_: AgentEventType, run_id: str, **data: Any) -> AgentEvent:
    return AgentEvent(type=type_, run_id=run_id, data=data)
