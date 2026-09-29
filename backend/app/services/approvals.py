import uuid
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import remote
from app.agent.tools import TOOLS, AgentContext
from app.core.errors import AppError, ConflictError, ValidationFailed
from app.core.timeutils import as_utc, utcnow
from app.models import AgentRun, Approval, Message, ToolCall, User
from app.models.enums import AgentRunStatus, ApprovalStatus, NotificationType, ToolCallStatus
from app.notifications import notify
from app.repositories.base import get_owned, paginate
from app.services import audit


def list_approvals(
    db: Session, user: User, *, page: int, page_size: int, status: list[ApprovalStatus] | None = None
) -> tuple[list[Approval], int]:
    expire_due(db, user_id=user.id)
    stmt = select(Approval).where(Approval.user_id == user.id)
    if status:
        stmt = stmt.where(Approval.status.in_(status))
    return paginate(db, stmt.order_by(Approval.created_at.desc()), page, page_size)


def get_approval(db: Session, user: User, approval_id: uuid.UUID) -> Approval:
    return get_owned(db, Approval, approval_id, user.id, label="Approval")


def approve(
    db: Session, user: User, tz: ZoneInfo, approval_id: uuid.UUID, *, ip: str | None = None, user_token: str | None = None
) -> Approval:
    approval = _pending(db, user, approval_id)
    from_agent_core = (approval.payload or {}).get("source") == remote.SOURCE
    tool = None if from_agent_core else TOOLS.get(approval.action)
    call = db.get(ToolCall, approval.tool_call_id) if approval.tool_call_id else None
    if not from_agent_core and tool is None:
        raise ConflictError("This action is no longer supported")
    if from_agent_core and not user_token:
        raise ConflictError("This action must be approved from the app")

    try:
        if from_agent_core:
            # Validated here (owner, pending, not expired); executed by the Agent Core's own tool
            # with exactly the stored payload, through this API with the user's token.
            result = remote.execute_action(approval, user_token or "")
        else:
            assert tool is not None
            with db.begin_nested():
                result = tool.apply(AgentContext(db, user, tz), (approval.payload or {}).get("args", {}))
    except (AppError, ValidationError) as exc:
        # Things may have changed since the proposal (e.g. the bill was deleted). Keep it pending so the
        # user can reject it, and record why it failed.
        message = exc.message if isinstance(exc, AppError) else "the proposed values are no longer valid"
        if call:
            call.error = f"Apply failed: {message}"
        db.commit()
        raise ValidationFailed(f"Couldn't apply this action: {message}", code="APPROVAL_APPLY_FAILED")

    now = utcnow()
    approval.status = ApprovalStatus.APPROVED
    approval.responded_at = now
    approval.result = result
    if call:
        call.status = ToolCallStatus.COMPLETED
        call.output = {**(call.output or {}), "status": "applied", "result": result}
        call.error = None
    _sync_message(db, approval)
    _settle_run(db, approval.agent_run_id)
    notify(
        db, user, NotificationType.AGENT_ACTION, f"{approval.action_label}: done", result.get("summary", approval.title),
        meta={"approvalId": str(approval.id), **{k: result[k] for k in ("resource_type", "resource_id") if k in result}},
    )
    audit.record(
        db, "approval.approved", user_id=user.id, resource_type="approval", resource_id=approval.id, ip_address=ip,
        details={"action": approval.action, "result": result},
    )
    db.commit()
    return approval


def reject(
    db: Session, user: User, approval_id: uuid.UUID, *, reason: str | None = None, ip: str | None = None
) -> Approval:
    approval = _pending(db, user, approval_id)
    approval.status = ApprovalStatus.REJECTED
    approval.responded_at = utcnow()
    approval.result = {"reason": reason} if reason else None
    _skip_call(db, approval)
    _sync_message(db, approval)
    _settle_run(db, approval.agent_run_id)
    audit.record(
        db, "approval.rejected", user_id=user.id, resource_type="approval", resource_id=approval.id, ip_address=ip,
        details={"action": approval.action},
    )
    db.commit()
    return approval


def expire_due(db: Session, *, user_id: uuid.UUID | None = None) -> int:
    """Expire pending approvals past their TTL. Commits only if something changed."""
    stmt = select(Approval).where(Approval.status == ApprovalStatus.PENDING, Approval.expires_at <= utcnow())
    if user_id:
        stmt = stmt.where(Approval.user_id == user_id)
    expired = list(db.scalars(stmt))
    for approval in expired:
        _expire(db, approval)
    if expired:
        db.commit()
    return len(expired)


def _pending(db: Session, user: User, approval_id: uuid.UUID) -> Approval:
    approval = get_approval(db, user, approval_id)
    if approval.status == ApprovalStatus.PENDING and approval.expires_at and as_utc(approval.expires_at) <= utcnow():
        _expire(db, approval)
        db.commit()
    if approval.status != ApprovalStatus.PENDING:
        raise ConflictError(f"This action was already {approval.status.value}", code="APPROVAL_NOT_PENDING")
    return approval


def _expire(db: Session, approval: Approval) -> None:
    approval.status = ApprovalStatus.EXPIRED
    _skip_call(db, approval)
    _sync_message(db, approval)
    _settle_run(db, approval.agent_run_id)


def _skip_call(db: Session, approval: Approval) -> None:
    if approval.tool_call_id and (call := db.get(ToolCall, approval.tool_call_id)):
        call.status = ToolCallStatus.SKIPPED
        call.completed_at = call.completed_at or utcnow()


def _sync_message(db: Session, approval: Approval) -> None:
    """Keep the action card in the chat transcript in step with the approval."""
    if not approval.message_id or not (message := db.get(Message, approval.message_id)):
        return
    meta = dict(message.meta or {})
    meta["actions"] = [
        {**a, "status": approval.status.value} if a.get("approvalId") == str(approval.id) else a
        for a in meta.get("actions", [])
    ]
    message.meta = meta  # reassign so the JSON column is flagged dirty


def _settle_run(db: Session, run_id: uuid.UUID | None) -> None:
    """A run waiting for approval completes once none of its approvals are pending."""
    if run_id is None:
        return
    db.flush()
    run = db.get(AgentRun, run_id)
    if run is None or run.status != AgentRunStatus.WAITING_FOR_APPROVAL:
        return
    still_pending = db.scalar(
        select(Approval.id).where(Approval.agent_run_id == run_id, Approval.status == ApprovalStatus.PENDING).limit(1)
    )
    if still_pending is None:
        run.status = AgentRunStatus.COMPLETED
        run.completed_at = utcnow()
