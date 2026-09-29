"""Documents, conversations, agent runs, approvals, notifications and audit logs."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, func, BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAt, Timestamps, UserOwned, UUIDPk, str_enum
from app.models.enums import (
    AgentRunStatus,
    ApprovalStatus,
    DocumentStatus,
    MessageRole,
    NotificationStatus,
    NotificationType,
    ToolCallStatus,
)


class Document(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    category: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[DocumentStatus] = mapped_column(str_enum(DocumentStatus), default=DocumentStatus.UPLOADING)
    page_count: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(UUIDPk, Timestamps, UserOwned, Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_updated", "user_id", "updated_at"),)

    title: Mapped[str] = mapped_column(String(200), default="New Conversation")

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True
    )


class Message(UUIDPk, CreatedAt, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[MessageRole] = mapped_column(str_enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    # `metadata` is reserved by SQLAlchemy's declarative API, hence the attribute name.
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="SET NULL"))

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AgentRun(UUIDPk, CreatedAt, UserOwned, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("user_id", "run_number", name="uq_agent_runs_user_run_number"),
        Index("ix_agent_runs_user_created", "user_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), index=True
    )
    run_number: Mapped[int] = mapped_column(Integer)
    request: Mapped[str] = mapped_column(Text)
    status: Mapped[AgentRunStatus] = mapped_column(str_enum(AgentRunStatus), default=AgentRunStatus.QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    tool_calls: Mapped[list["ToolCall"]] = relationship(
        back_populates="agent_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ToolCall.created_at",
    )


class ToolCall(UUIDPk, CreatedAt, Base):
    __tablename__ = "tool_calls"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    tool_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[ToolCallStatus] = mapped_column(str_enum(ToolCallStatus), default=ToolCallStatus.PENDING)
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    agent_run: Mapped[AgentRun] = relationship(back_populates="tool_calls")


class Approval(UUIDPk, Timestamps, UserOwned, Base):
    """An agent action held until the user decides. `action`/`payload` describe the tool to run on approval."""

    __tablename__ = "approvals"
    __table_args__ = (Index("ix_approvals_user_status", "user_id", "status"),)

    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    tool_call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tool_calls.id", ondelete="SET NULL"))
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100))
    action_label: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[ApprovalStatus] = mapped_column(str_enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict | None] = mapped_column(JSON)


class Notification(UUIDPk, CreatedAt, UserOwned, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
        Index("ix_notifications_status_scheduled", "status", "scheduled_at"),
        # Idempotency for scheduler-generated notifications (e.g. one per reminder occurrence).
        UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
    )

    type: Mapped[NotificationType] = mapped_column(str_enum(NotificationType))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[NotificationStatus] = mapped_column(
        str_enum(NotificationStatus), default=NotificationStatus.SCHEDULED
    )
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    dedupe_key: Mapped[str | None] = mapped_column(String(200))
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class AuditLog(UUIDPk, CreatedAt, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
