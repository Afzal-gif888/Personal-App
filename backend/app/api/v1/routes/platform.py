"""Documents, conversations, agent runs, approvals, notifications and the dashboard."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import DB, AccessToken, CurrentUser, Paging, UserZone, client_ip
from app.core.rate_limit import rate_limit
from app.models.enums import AgentRunStatus, ApprovalStatus, DocumentStatus
from app.schemas.common import Page
from app.schemas.platform import (
    AgentRunDetail,
    AgentRunOut,
    ApprovalOut,
    ConversationIn,
    ConversationOut,
    ConversationUpdate,
    DashboardOut,
    DocumentOut,
    DocumentUpdate,
    MessageIn,
    MessageOut,
    NotificationOut,
    RejectIn,
    SendMessageOut,
    UnreadCount,
)
from app.services import agent_runs, approvals, chat, dashboard, documents, notifications
from app.storage import get_storage

router = APIRouter()

# --- Documents ------------------------------------------------------------------------------------


@router.get("/documents", response_model=Page[DocumentOut], tags=["documents"])
def list_documents(
    user: CurrentUser,
    db: DB,
    paging: Paging,
    category: Annotated[str | None, Query(max_length=100)] = None,
    doc_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
):
    items, total = documents.list_documents(
        db, user, page=paging.page, page_size=paging.page_size, category=category, status=doc_status, q=q
    )
    return Page(items=[documents.to_out(d) for d in items], total=total, page=paging.page, page_size=paging.page_size)


@router.post("/documents", response_model=DocumentOut, status_code=201, tags=["documents"])
def upload_document(
    user: CurrentUser,
    db: DB,
    file: Annotated[UploadFile, File()],
    category: Annotated[str | None, Form(max_length=100)] = None,
):
    return documents.to_out(documents.upload(db, user, file.filename or "", file.file, category))


@router.get("/documents/{doc_id}", response_model=DocumentOut, tags=["documents"])
def get_document(doc_id: uuid.UUID, user: CurrentUser, db: DB):
    return documents.to_out(documents.get_document(db, user, doc_id))


@router.get("/documents/{doc_id}/download", tags=["documents"])
def download_document(doc_id: uuid.UUID, user: CurrentUser, db: DB):
    doc = documents.get_document(db, user, doc_id)
    return FileResponse(
        get_storage().path(doc.storage_key),
        media_type=doc.mime_type,
        filename=doc.original_filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.patch("/documents/{doc_id}", response_model=DocumentOut, tags=["documents"])
def update_document(doc_id: uuid.UUID, data: DocumentUpdate, user: CurrentUser, db: DB):
    return documents.to_out(documents.update_document(db, user, doc_id, data))


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["documents"])
def delete_document(doc_id: uuid.UUID, user: CurrentUser, db: DB, request: Request):
    documents.delete_document(db, user, doc_id, ip=client_ip(request))


# --- Conversations --------------------------------------------------------------------------------


@router.get("/conversations", response_model=list[ConversationOut], tags=["chat"])
def list_conversations(user: CurrentUser, db: DB):
    return chat.list_conversations(db, user)


@router.post("/conversations", response_model=ConversationOut, status_code=201, tags=["chat"])
def create_conversation(user: CurrentUser, db: DB, data: ConversationIn | None = None):
    return chat.create_conversation(db, user, data.title if data else None)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut, tags=["chat"])
def get_conversation(conversation_id: uuid.UUID, user: CurrentUser, db: DB):
    return chat.get_conversation(db, user, conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut, tags=["chat"])
def rename_conversation(conversation_id: uuid.UUID, data: ConversationUpdate, user: CurrentUser, db: DB):
    return chat.rename_conversation(db, user, conversation_id, data.title)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["chat"])
def delete_conversation(conversation_id: uuid.UUID, user: CurrentUser, db: DB):
    chat.delete_conversation(db, user, conversation_id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut], tags=["chat"])
def list_messages(conversation_id: uuid.UUID, user: CurrentUser, db: DB):
    return [MessageOut.from_model(m) for m in chat.list_messages(db, user, conversation_id)]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageOut,
    status_code=201,
    tags=["chat"],
    dependencies=[Depends(rate_limit("chat", "rate_limit_chat_per_minute"))],
)
def send_message(conversation_id: uuid.UUID, data: MessageIn, user: CurrentUser, db: DB, tz: UserZone, token: AccessToken):
    """Send a message and run the agent. Proposed changes come back as pending approvals in
    `assistantMessage.metadata.actions`; nothing is changed until they are approved."""
    user_msg, assistant_msg, run, conversation = chat.send_message(
        db, user, tz, conversation_id, data.content, user_token=token
    )
    return SendMessageOut(
        user_message=MessageOut.from_model(user_msg),
        assistant_message=MessageOut.from_model(assistant_msg),
        agent_run=agent_runs.to_out(run),
        conversation=ConversationOut.model_validate(conversation),
    )


@router.delete("/conversations/{conversation_id}/messages", status_code=status.HTTP_204_NO_CONTENT, tags=["chat"])
def clear_messages(conversation_id: uuid.UUID, user: CurrentUser, db: DB):
    chat.clear_messages(db, user, conversation_id)


# --- Agent runs -----------------------------------------------------------------------------------


@router.get("/agent-runs", response_model=Page[AgentRunOut], tags=["agent"])
def list_agent_runs(
    user: CurrentUser, db: DB, paging: Paging, run_status: Annotated[AgentRunStatus | None, Query(alias="status")] = None
):
    items, total = agent_runs.list_runs(db, user, page=paging.page, page_size=paging.page_size, status=run_status)
    return Page(items=[agent_runs.to_out(r) for r in items], total=total, page=paging.page, page_size=paging.page_size)


@router.get("/agent-runs/{run_id}", response_model=AgentRunDetail, tags=["agent"])
def get_agent_run(run_id: uuid.UUID, user: CurrentUser, db: DB):
    return agent_runs.get_run_detail(db, user, run_id)


# --- Approvals ------------------------------------------------------------------------------------


@router.get("/approvals", response_model=Page[ApprovalOut], tags=["approvals"])
def list_approvals(
    user: CurrentUser,
    db: DB,
    paging: Paging,
    approval_status: Annotated[list[ApprovalStatus] | None, Query(alias="status")] = None,
):
    items, total = approvals.list_approvals(
        db, user, page=paging.page, page_size=paging.page_size, status=approval_status
    )
    return Page(items=[ApprovalOut.from_model(a) for a in items], total=total, page=paging.page, page_size=paging.page_size)


@router.get("/approvals/{approval_id}", response_model=ApprovalOut, tags=["approvals"])
def get_approval(approval_id: uuid.UUID, user: CurrentUser, db: DB):
    return ApprovalOut.from_model(approvals.get_approval(db, user, approval_id))


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalOut, tags=["approvals"])
def approve(approval_id: uuid.UUID, user: CurrentUser, db: DB, tz: UserZone, request: Request, token: AccessToken):
    """Run the proposed action exactly as previewed. `result` holds the created resource id."""
    return ApprovalOut.from_model(approvals.approve(db, user, tz, approval_id, ip=client_ip(request), user_token=token))


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalOut, tags=["approvals"])
def reject(approval_id: uuid.UUID, user: CurrentUser, db: DB, request: Request, data: RejectIn | None = None):
    return ApprovalOut.from_model(
        approvals.reject(db, user, approval_id, reason=data.reason if data else None, ip=client_ip(request))
    )


# --- Notifications --------------------------------------------------------------------------------


@router.get("/notifications", response_model=Page[NotificationOut], tags=["notifications"])
def list_notifications(user: CurrentUser, db: DB, paging: Paging, unread_only: bool = False):
    items, total = notifications.list_notifications(
        db, user, page=paging.page, page_size=paging.page_size, unread_only=unread_only
    )
    return Page(
        items=[NotificationOut.from_model(n) for n in items], total=total, page=paging.page, page_size=paging.page_size
    )


@router.get("/notifications/unread-count", response_model=UnreadCount, tags=["notifications"])
def unread_count(user: CurrentUser, db: DB):
    return UnreadCount(unread=notifications.unread_count(db, user))


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT, tags=["notifications"])
def read_all(user: CurrentUser, db: DB):
    notifications.read_all(db, user)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut, tags=["notifications"])
def read_one(notification_id: uuid.UUID, user: CurrentUser, db: DB):
    return NotificationOut.from_model(notifications.read_one(db, user, notification_id))


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["notifications"])
def delete_notification(notification_id: uuid.UUID, user: CurrentUser, db: DB):
    notifications.delete(db, user, notification_id)


# --- Dashboard ------------------------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardOut, tags=["dashboard"])
def get_dashboard(user: CurrentUser, db: DB, tz: UserZone):
    return dashboard.summary(db, user, tz)
