"""Agent run request/response contracts and the value objects carried in agent state."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.memory import ConversationTurn
from app.schemas.tool import ToolCallRecord, ToolDomain


class RunStatus(StrEnum):
    COMPLETED = "completed"
    APPROVAL_REQUIRED = "approval_required"
    INCOMPLETE = "incomplete"  # stopped by a loop-safety limit
    FAILED = "failed"


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    LLM_ERROR = "LLM_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    ITERATION_LIMIT = "ITERATION_LIMIT"
    TOOL_LIMIT = "TOOL_LIMIT"
    INVALID_STATE = "INVALID_STATE"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AgentError(BaseModel):
    """User-safe error. Never carries stack traces or provider internals."""

    code: ErrorCode
    message: str
    retryable: bool = False


class UserContext(BaseModel):
    """Who the run is for, as confirmed by the backend (never taken from the caller's word)."""

    user_id: str
    name: str = ""
    timezone: str = "UTC"
    currency: str = "INR"
    preferences: dict[str, Any] = Field(default_factory=dict)


class Intent(BaseModel):
    """Deterministic understanding of the request, used to scope context, tools and retrieval."""

    domains: list[ToolDomain] = Field(default_factory=list)
    needs_documents: bool = False
    wants_change: bool = False
    multi_step: bool = False


class Observation(BaseModel):
    """A compact note about one tool result, fed back into planning and the final summary."""

    tool_call_id: str
    tool_name: str
    ok: bool
    summary: str


class ApprovalRequest(BaseModel):
    """Returned when an action needs the user's go-ahead. `action_payload` is exactly what will run."""

    approval_id: str
    action_type: str
    action_payload: dict[str, Any]
    reason: str
    expires_at: datetime


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = Field(default=None, max_length=64)
    # Optional: when sent, it must match the user the backend token belongs to.
    user_id: str | None = Field(default=None, max_length=64)
    # Optional prior turns; when omitted and conversation_id is set, history is fetched from the backend.
    history: list[ConversationTurn] | None = Field(default=None, max_length=200)

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class AgentRunResponse(BaseModel):
    run_id: str
    status: RunStatus
    response: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    approval_required: bool = False
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    retrieved_documents: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    error: AgentError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    status: str
    result: dict[str, Any] | None = None
    error: AgentError | None = None
