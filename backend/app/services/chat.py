import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agent.remote import run_remote_agent
from app.agent.runner import AgentOutcome, run_agent
from app.agent.tools import AgentContext
from app.core.config import get_settings
from app.core.timeutils import utcnow
from app.llm import get_provider
from app.models import AgentRun, Conversation, Message, User
from app.models.enums import MessageRole
from app.repositories.base import apply_patch, get_owned

DEFAULT_TITLE = "New Conversation"


def list_conversations(db: Session, user: User, *, limit: int = 100) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
    )


def get_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> Conversation:
    return get_owned(db, Conversation, conversation_id, user.id, label="Conversation")


def create_conversation(db: Session, user: User, title: str | None) -> Conversation:
    conversation = Conversation(user_id=user.id, title=title or DEFAULT_TITLE)
    db.add(conversation)
    db.commit()
    return conversation


def rename_conversation(db: Session, user: User, conversation_id: uuid.UUID, title: str) -> Conversation:
    conversation = get_conversation(db, user, conversation_id)
    apply_patch(conversation, {"title": title})
    db.commit()
    return conversation


def delete_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> None:
    db.delete(get_conversation(db, user, conversation_id))
    db.commit()


def list_messages(db: Session, user: User, conversation_id: uuid.UUID, *, limit: int = 200) -> list[Message]:
    get_conversation(db, user, conversation_id)
    return _recent(db, conversation_id, limit)


def clear_messages(db: Session, user: User, conversation_id: uuid.UUID) -> None:
    get_conversation(db, user, conversation_id)
    db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    db.commit()


def _history(db: Session, conversation_id: uuid.UUID) -> list[dict]:
    """Recent user/assistant text turns as model input. Failed turns are left out."""
    rows = _recent(db, conversation_id, get_settings().agent_history_messages)
    history = [
        {"role": m.role.value, "content": m.content}
        for m in rows
        if m.role in (MessageRole.USER, MessageRole.ASSISTANT) and (m.meta or {}).get("status") != "error"
    ]
    while history and history[0]["role"] != "user":  # the model expects the transcript to open with the user
        history.pop(0)
    return history


def _recent(db: Session, conversation_id: uuid.UUID, limit: int) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    return list(reversed(list(db.scalars(stmt))))


def send_message(
    db: Session, user: User, tz: ZoneInfo, conversation_id: uuid.UUID, content: str, *, user_token: str | None = None
) -> tuple[Message, Message, AgentRun, Conversation]:
    conversation = get_conversation(db, user, conversation_id)
    history = _history(db, conversation.id)

    # Explicit timestamps: server-side now() is the transaction start and would tie both messages.
    user_message = Message(
        conversation_id=conversation.id, role=MessageRole.USER, content=content, meta={}, created_at=utcnow()
    )
    db.add(user_message)
    if conversation.title == DEFAULT_TITLE:
        conversation.title = content[:60] + ("…" if len(content) > 60 else "")
    db.flush()

    if get_settings().agent_core_mode == "agent" and user_token:
        # The Agent Core's LangGraph agent reasons and acts; this service persists the run.
        outcome = run_remote_agent(
            db, user, user_token=user_token, request=content, history=history, conversation_id=conversation.id
        )
    else:
        outcome = run_agent(
            db,
            AgentContext(db, user, tz),
            get_provider(),
            request=content,
            history=history,
            conversation_id=conversation.id,
        )
    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=outcome.reply,
        meta=_metadata(outcome),
        agent_run_id=outcome.run.id,
        created_at=utcnow(),
    )
    db.add(assistant_message)
    db.flush()
    user_message.agent_run_id = outcome.run.id
    for approval in outcome.approvals:
        approval.message_id = assistant_message.id
    conversation.updated_at = utcnow()
    db.commit()
    return user_message, assistant_message, outcome.run, conversation


def _metadata(outcome: AgentOutcome) -> dict:
    meta = {
        "status": "error" if outcome.error else "success",
        "steps": outcome.steps,
        "actions": [
            {
                "approvalId": str(a.id),
                "action": a.action,
                "actionLabel": a.action_label,
                "title": a.title,
                "description": a.description,
                "details": a.payload.get("details", {}),
                "status": a.status.value,
            }
            for a in outcome.approvals
        ],
    }
    if outcome.error:
        meta["error"] = outcome.error
    return meta
