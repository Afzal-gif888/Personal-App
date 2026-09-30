import uuid
from datetime import date as Date
from typing import Any

from pydantic import Field

from app.models.enums import (
    AgentRunStatus,
    ApprovalStatus,
    DocumentIndexStatus,
    DocumentStatus,
    MessageRole,
    NotificationStatus,
    NotificationType,
    ToolCallStatus,
)
from app.schemas.common import APIModel, InputModel, Money, UTCDateTime
from app.schemas.finance import BillOut
from app.schemas.planning import GoalOut, TaskOut

# --- Documents ------------------------------------------------------------------------------------


class DocumentOut(APIModel):
    id: uuid.UUID
    name: str
    mime_type: str
    size: int
    category: str | None
    status: DocumentStatus
    page_count: int | None
    checksum_sha256: str | None
    error_message: str | None
    uploaded_at: UTCDateTime
    processed_at: UTCDateTime | None
    download_url: str
    # Document search: "indexed" means the assistant can search this document's content.
    index_status: DocumentIndexStatus
    index_error: str | None = None
    chunk_count: int = 0
    indexed_at: UTCDateTime | None = None


class DocumentSearchIn(InputModel):
    query: str = Field(min_length=2, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    document_ids: list[uuid.UUID] | None = Field(default=None, max_length=20)


class DocumentSearchHitOut(APIModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    chunk_index: int
    page_number: int | None
    content: str
    similarity: float


class DocumentSearchOut(APIModel):
    query: str
    results: list[DocumentSearchHitOut]
    message: str | None = None  # set when nothing relevant was found


class DocumentUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)


# --- Conversations & messages ---------------------------------------------------------------------


class ConversationIn(InputModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class ConversationUpdate(InputModel):
    title: str = Field(min_length=1, max_length=200)


class ConversationOut(APIModel):
    id: uuid.UUID
    title: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


class MessageIn(InputModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageOut(APIModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    # steps: the agent's tool trace; actions: proposed changes awaiting (or past) approval;
    # status: "success" | "error"; error: user-safe error text.
    metadata: dict[str, Any]
    agent_run_id: uuid.UUID | None
    created_at: UTCDateTime

    @classmethod
    def from_model(cls, m) -> "MessageOut":
        return cls(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            metadata=m.meta or {},
            agent_run_id=m.agent_run_id,
            created_at=m.created_at,
        )


# --- Agent runs, tool calls, approvals ------------------------------------------------------------


class ToolCallOut(APIModel):
    id: uuid.UUID
    tool_name: str
    status: ToolCallStatus
    input: dict[str, Any]
    output: dict[str, Any] | None
    error: str | None
    started_at: UTCDateTime | None
    completed_at: UTCDateTime | None
    duration_ms: int | None
    created_at: UTCDateTime


class ApprovalOut(APIModel):
    id: uuid.UUID
    agent_run_id: uuid.UUID | None
    message_id: uuid.UUID | None
    action: str
    action_label: str
    title: str
    description: str | None
    details: dict[str, Any]
    status: ApprovalStatus
    expires_at: UTCDateTime | None
    responded_at: UTCDateTime | None
    result: dict[str, Any] | None
    created_at: UTCDateTime

    @classmethod
    def from_model(cls, a) -> "ApprovalOut":
        return cls(
            id=a.id,
            agent_run_id=a.agent_run_id,
            message_id=a.message_id,
            action=a.action,
            action_label=a.action_label,
            title=a.title,
            description=a.description,
            details=(a.payload or {}).get("details", {}),
            status=a.status,
            expires_at=a.expires_at,
            responded_at=a.responded_at,
            result=a.result,
            created_at=a.created_at,
        )


class RejectIn(InputModel):
    reason: str | None = Field(default=None, max_length=1000)


class AgentRunOut(APIModel):
    id: uuid.UUID
    run_number: int
    conversation_id: uuid.UUID | None
    request: str
    status: AgentRunStatus
    started_at: UTCDateTime | None
    completed_at: UTCDateTime | None
    duration_ms: int | None
    error_message: str | None
    tools_used: list[str]
    created_at: UTCDateTime


class AgentRunDetail(AgentRunOut):
    tool_calls: list[ToolCallOut]
    approvals: list[ApprovalOut]


class SendMessageOut(APIModel):
    user_message: MessageOut
    assistant_message: MessageOut
    agent_run: AgentRunOut | None
    conversation: ConversationOut


# --- Notifications --------------------------------------------------------------------------------


class NotificationOut(APIModel):
    id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    status: NotificationStatus
    channel: str
    scheduled_at: UTCDateTime | None
    sent_at: UTCDateTime | None
    read_at: UTCDateTime | None
    metadata: dict[str, Any]
    created_at: UTCDateTime

    @classmethod
    def from_model(cls, n) -> "NotificationOut":
        return cls.model_validate(
            {
                **{c.key: getattr(n, c.key) for c in n.__table__.columns if c.key != "meta"},
                "metadata": n.meta or {},
            }
        )


class UnreadCount(APIModel):
    unread: int


# --- Dashboard ------------------------------------------------------------------------------------


class DashboardStats(APIModel):
    tasks_due_today: int
    overdue_tasks: int
    open_tasks: int
    pending_approvals: int
    unread_notifications: int
    study_minutes_today: int
    daily_study_goal_minutes: int
    upcoming_bills_total: Money
    month_spend: Money
    currency: str


class ScheduleItem(APIModel):
    kind: str  # "event" | "study_session"
    id: uuid.UUID
    title: str
    date: Date
    start_time: str
    end_time: str | None


class DashboardOut(APIModel):
    stats: DashboardStats
    tasks_due_soon: list[TaskOut]
    schedule: list[ScheduleItem]
    pending_approvals: list[ApprovalOut]
    upcoming_bills: list[BillOut]
    active_goals: list[GoalOut]
