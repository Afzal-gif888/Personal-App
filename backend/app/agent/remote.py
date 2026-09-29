"""Run the Agent Core's LangGraph agent (AGENT_CORE_MODE=agent) and persist what it did.

The Agent Core owns reasoning: planning, tool selection, tool execution through this API with the
user's own token, observations, memory and RAG. This module owns persistence. Every run, tool call
and approval request it reports becomes an `agent_runs` / `tool_calls` / `approvals` row, so the
Agent runs and Approvals pages show real data and decisions survive restarts.

Approving an Agent Core action calls its `/agent/actions/execute` endpoint, which runs exactly the
stored payload. The approval itself is validated here (owner, pending, not expired) first.
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.agent.runner import AgentOutcome, _skip_pending, create_run
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import redact
from app.core.timeutils import as_utc, utcnow
from app.models import AgentRun, Approval, ToolCall, User
from app.models.enums import AgentRunStatus, ApprovalStatus, ToolCallStatus

logger = logging.getLogger(__name__)

SOURCE = "agent_core"  # approvals.payload["source"] for actions the Agent Core must execute
_TOOL_STATUS = {
    "completed": ToolCallStatus.COMPLETED,
    "failed": ToolCallStatus.FAILED,
    "approval_required": ToolCallStatus.WAITING_FOR_APPROVAL,
    "skipped": ToolCallStatus.SKIPPED,
}


class AgentCoreActionError(AppError):
    status_code = 422
    code = "APPROVAL_APPLY_FAILED"


def _post(path: str, body: dict[str, Any], user_token: str) -> httpx.Response:
    settings = get_settings()
    return httpx.post(
        settings.agent_core_url.rstrip("/") + path,
        json=body,
        headers={
            "Authorization": f"Bearer {settings.agent_core_service_token}",
            # The Agent Core calls this API back with the user's own token, so it can only ever
            # reach this user's data.
            "X-User-Authorization": f"Bearer {user_token}",
        },
        timeout=settings.agent_core_timeout_seconds,
    )


def _label(action: str) -> str:
    return action.replace("_", " ").capitalize()


def _details(payload: dict[str, Any]) -> dict[str, Any]:
    return {k.replace("_", " ").capitalize(): v for k, v in payload.items() if not k.endswith("_id")}


def _title(label: str, payload: dict[str, Any]) -> str:
    name = payload.get("title") or payload.get("name") or payload.get("subject") or payload.get("topic")
    return f"{label}: {name}" if name else label


def _expiry(raw: Any, fallback: datetime) -> datetime:
    try:
        return min(as_utc(datetime.fromisoformat(str(raw))), fallback)
    except (TypeError, ValueError):
        return fallback


def run_remote_agent(
    db: Session,
    user: User,
    *,
    user_token: str,
    request: str,
    history: list[dict[str, Any]],
    conversation_id: uuid.UUID | None,
) -> AgentOutcome:
    run = create_run(db, user, request, conversation_id)
    outcome = AgentOutcome(run=run, reply="")
    started = time.monotonic()
    body = {
        "message": request,
        "conversation_id": str(conversation_id) if conversation_id else None,
        "user_id": str(user.id),
        "history": history,
    }
    data: dict[str, Any] | None = None
    try:
        resp = _post("/agent/run", body, user_token)
        parsed = resp.json()
        if isinstance(parsed, dict) and "status" in parsed:
            data = parsed
        else:
            logger.error("Agent Core rejected the run", extra={"status": resp.status_code})
            _fail(run, outcome, "The assistant service is misconfigured. Please contact the administrator.")
    except httpx.HTTPError:
        _fail(run, outcome, "Couldn't reach the assistant service. Please try again.")
    except ValueError:
        _fail(run, outcome, "The assistant service sent an invalid response.")
    if data is not None:
        _record(db, user, run, data, outcome)

    run.duration_ms = int((time.monotonic() - started) * 1000)
    if run.status != AgentRunStatus.WAITING_FOR_APPROVAL:
        run.completed_at = utcnow()
    db.flush()
    return outcome


def _fail(run: AgentRun, outcome: AgentOutcome, message: str) -> None:
    run.status = AgentRunStatus.FAILED
    run.error_message = message
    run.meta = {"provider": SOURCE, "engine": "langgraph", "tools_used": []}
    outcome.error = outcome.reply = message


def _record(db: Session, user: User, run: AgentRun, data: dict[str, Any], outcome: AgentOutcome) -> None:
    now = utcnow()
    calls_by_approval: dict[str, ToolCall] = {}
    for rec in data.get("tool_calls") or []:
        status = _TOOL_STATUS.get(rec.get("status"), ToolCallStatus.FAILED)
        call = ToolCall(
            agent_run_id=run.id,
            tool_name=str(rec.get("name", ""))[:100],
            status=status,
            input=redact(rec.get("input") or {}),
            output=rec.get("output"),
            error=rec.get("error"),
            started_at=now,
            completed_at=None if status == ToolCallStatus.WAITING_FOR_APPROVAL else now,
            duration_ms=int(rec.get("duration_ms") or 0),
            created_at=utcnow(),  # ordered by this; server now() would tie within the transaction
        )
        db.add(call)
        db.flush()
        if rec.get("approval_id"):
            calls_by_approval[rec["approval_id"]] = call
        outcome.steps.append({
            "id": str(call.id),
            "title": _label(call.tool_name),
            "status": "failed" if status == ToolCallStatus.FAILED else "completed",
            "toolName": call.tool_name,
            "toolInput": call.input,
            "toolOutput": call.output if call.output is not None else ({"error": call.error} if call.error else None),
            "timestamp": now.isoformat(),
        })

    latest_expiry = now + timedelta(hours=get_settings().approval_ttl_hours)
    for req in data.get("approvals") or []:
        payload = req.get("action_payload") or {}
        label = _label(str(req.get("action_type", "")))
        call = calls_by_approval.get(req.get("approval_id", ""))
        approval = Approval(
            user_id=user.id,
            agent_run_id=run.id,
            tool_call_id=call.id if call else None,
            action=str(req.get("action_type", ""))[:100],
            action_label=label[:100],
            title=_title(label, payload)[:300],
            description=req.get("reason"),
            payload={"source": SOURCE, "args": payload, "details": _details(payload),
                     "agent_core_approval_id": req.get("approval_id")},
            status=ApprovalStatus.PENDING,
            expires_at=_expiry(req.get("expires_at"), latest_expiry),
        )
        db.add(approval)
        db.flush()
        outcome.approvals.append(approval)
        if call:
            call.output = {"status": "pending_approval", "approval_id": str(approval.id)}

    outcome.reply = data.get("response") or ""
    error = data.get("error") or {}
    status = data.get("status")
    if status == "failed":
        run.status = AgentRunStatus.FAILED
        message = error.get("message") or "The assistant couldn't complete that."
        run.error_message = outcome.error = message
        outcome.reply = outcome.reply or message
        _skip_pending(db, outcome)
    elif outcome.approvals:
        run.status = AgentRunStatus.WAITING_FOR_APPROVAL
    else:
        run.status = AgentRunStatus.COMPLETED
        if status == "incomplete":  # stopped by a loop-safety limit; the reply explains what was done
            run.error_message = error.get("message")
    meta = data.get("metadata") or {}
    run.meta = {
        "provider": SOURCE,
        "engine": "langgraph",
        "agent_core_run_id": data.get("run_id"),
        "model": meta.get("model"),
        "tools_used": sorted({s["toolName"] for s in outcome.steps}),
        "events": [e.get("type") for e in data.get("events") or []],
        "iterations": meta.get("iterations"),
        "incomplete": status == "incomplete",
    }


def execute_action(approval: Approval, user_token: str) -> dict[str, Any]:
    """Have the Agent Core run an approved action. Raises AgentCoreActionError on failure."""
    args = (approval.payload or {}).get("args", {})
    try:
        resp = _post("/agent/actions/execute", {"action_type": approval.action, "action_payload": args}, user_token)
        data = resp.json()
    except httpx.HTTPError:
        raise AgentCoreActionError("Couldn't reach the assistant service. Please try again.")
    except ValueError:
        raise AgentCoreActionError("The assistant service sent an invalid response.")
    if resp.status_code != 200 or not isinstance(data, dict):
        message = (data.get("error") or {}).get("message") if isinstance(data, dict) else None
        raise AgentCoreActionError(message or "The assistant service couldn't apply this action.")
    result = data.get("result") or {}
    out: dict[str, Any] = {"summary": data.get("summary") or f"{approval.action_label} done", "result": result}
    if isinstance(result, dict) and result.get("id"):
        out["resource_id"] = str(result["id"])
        out["resource_type"] = approval.action.split("_", 1)[-1]
    return out
