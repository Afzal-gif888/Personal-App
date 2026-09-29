import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, Approval, User
from app.models.enums import AgentRunStatus
from app.repositories.base import get_owned, paginate
from app.schemas.platform import AgentRunDetail, AgentRunOut, ApprovalOut, ToolCallOut


def to_out(run: AgentRun) -> AgentRunOut:
    return AgentRunOut(
        id=run.id,
        run_number=run.run_number,
        conversation_id=run.conversation_id,
        request=run.request,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        error_message=run.error_message,
        tools_used=(run.meta or {}).get("tools_used", []),
        created_at=run.created_at,
    )


def list_runs(
    db: Session, user: User, *, page: int, page_size: int, status: AgentRunStatus | None = None
) -> tuple[list[AgentRun], int]:
    stmt = select(AgentRun).where(AgentRun.user_id == user.id)
    if status:
        stmt = stmt.where(AgentRun.status == status)
    return paginate(db, stmt.order_by(AgentRun.created_at.desc(), AgentRun.run_number.desc()), page, page_size)


def get_run_detail(db: Session, user: User, run_id: uuid.UUID) -> AgentRunDetail:
    run = get_owned(db, AgentRun, run_id, user.id, label="Agent run")
    run_approvals = db.scalars(select(Approval).where(Approval.agent_run_id == run.id).order_by(Approval.created_at))
    return AgentRunDetail(
        **to_out(run).model_dump(),
        tool_calls=[ToolCallOut.model_validate(c) for c in run.tool_calls],
        approvals=[ApprovalOut.from_model(a) for a in run_approvals],
    )
