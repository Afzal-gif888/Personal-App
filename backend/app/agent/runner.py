"""The agent loop: model <-> tools, with every write held for user approval."""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.tools import TOOLS, AgentContext, ToolInputError, tool_specs
from app.core.config import get_settings
from app.core.logging import redact
from app.core.timeutils import utcnow
from app.llm import LLMError, LLMProvider
from app.models import AgentRun, Approval, ToolCall, User
from app.models.enums import AgentRunStatus, ApprovalStatus, ToolCallStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are It's Personal, a personal assistant for a university student. You help with coursework, \
calendar, reminders, study plans, bills, expenses, budgets and goals, using the tools provided.

How you work:
- Look things up with the read tools before answering questions about the user's data. Never invent \
tasks, events, bills or numbers.
- Tools that create or change data (create_*, complete_task, log_expense, mark_bill_paid, set_budget) do not act \
immediately: each call becomes a proposal the user approves or rejects in the app. After proposing, \
tell the user briefly what you drafted and that it is waiting for their approval. Never claim that a \
proposed change has already been made.
- Only propose changes the user asked for or clearly agreed to. If a required detail (such as a date) \
is missing and can't be reasonably inferred, ask instead of guessing.
- Dates and times are in the user's local timezone. Resolve relative dates ("tomorrow", "next \
Friday") against today's date below.
- This app tracks payments; it cannot send money. Say so if asked to pay something.
- Keep replies short and practical. Use plain text with simple bullet lists when helpful.

Today is {today} ({weekday}); the user's timezone is {timezone}. The user's name is {name}."""


@dataclass
class AgentOutcome:
    run: AgentRun
    reply: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[Approval] = field(default_factory=list)
    error: str | None = None


def build_system_prompt(ctx: AgentContext) -> str:
    return SYSTEM_PROMPT.format(
        today=ctx.today.isoformat(),
        weekday=ctx.today.strftime("%A"),
        timezone=str(ctx.tz),
        name=ctx.user.name,
    )


def next_run_number(db: Session, user_id: uuid.UUID) -> int:
    return (db.scalar(select(func.max(AgentRun.run_number)).where(AgentRun.user_id == user_id)) or 1000) + 1


def create_run(db: Session, user: User, request: str, conversation_id: uuid.UUID | None) -> AgentRun:
    for _ in range(3):  # run numbers are per user; retry if a concurrent request took ours
        run = AgentRun(
            user_id=user.id,
            conversation_id=conversation_id,
            run_number=next_run_number(db, user.id),
            request=request,
            status=AgentRunStatus.RUNNING,
            started_at=utcnow(),
            meta={},
        )
        try:
            with db.begin_nested():
                db.add(run)
            return run
        except IntegrityError:
            continue
    raise RuntimeError("Could not allocate an agent run number")


def run_agent(
    db: Session,
    ctx: AgentContext,
    provider: LLMProvider,
    *,
    request: str,
    history: list[dict[str, Any]],
    conversation_id: uuid.UUID | None,
) -> AgentOutcome:
    """Run one user turn. Commits nothing: the caller owns the transaction."""
    settings = get_settings()
    run = create_run(db, ctx.user, request, conversation_id)
    started = time.monotonic()
    messages = [*history, {"role": "user", "content": request}]
    system = build_system_prompt(ctx)
    specs = tool_specs()
    outcome = AgentOutcome(run=run, reply="")
    response = None

    try:
        for _ in range(settings.agent_max_iterations):
            response = provider.complete(system=system, messages=messages, tools=specs)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                outcome.reply = "Sorry, I can't help with that request."
                break
            tool_uses = response.tool_uses
            if not tool_uses:
                outcome.reply = response.text or "Done."
                break

            results = [_handle_tool(db, ctx, run, use.id, use.name, use.input, outcome) for use in tool_uses]
            # All results for one assistant turn go back in a single user message.
            messages.append({"role": "user", "content": results})
        else:
            outcome.reply = (
                "I wasn't able to finish that within my step limit. Here's where I got to"
                + (": " + response.text if response and response.text else ".")
            )
        run.status = AgentRunStatus.WAITING_FOR_APPROVAL if outcome.approvals else AgentRunStatus.COMPLETED
    except LLMError as exc:
        outcome.error = exc.message
        outcome.reply = exc.message
        run.status = AgentRunStatus.FAILED
        run.error_message = exc.message
        _skip_pending(db, outcome)
    except Exception:
        logger.exception("Agent run crashed", extra={"agent_run_id": str(run.id)})
        outcome.error = "Something went wrong while working on that. Please try again."
        outcome.reply = outcome.error
        run.status = AgentRunStatus.FAILED
        run.error_message = "Internal error"
        _skip_pending(db, outcome)

    now = utcnow()
    run.duration_ms = int((time.monotonic() - started) * 1000)
    if run.status != AgentRunStatus.WAITING_FOR_APPROVAL:
        run.completed_at = now
    run.meta = {"provider": provider.name, "tools_used": sorted({s["toolName"] for s in outcome.steps})}
    db.flush()
    return outcome


def _handle_tool(
    db: Session, ctx: AgentContext, run: AgentRun, tool_use_id: str, name: str, raw_input: dict, outcome: AgentOutcome
) -> dict[str, Any]:
    tool = TOOLS.get(name)
    call = ToolCall(
        agent_run_id=run.id,
        tool_name=name,
        status=ToolCallStatus.RUNNING,
        input=redact(raw_input or {}),
        started_at=utcnow(),
        created_at=utcnow(),  # tool calls are ordered by this; server now() would tie within a transaction
    )
    db.add(call)
    db.flush()
    started = time.monotonic()

    def finish(status: ToolCallStatus, output: dict | None = None, error: str | None = None) -> None:
        call.status, call.output, call.error = status, output, error
        call.completed_at = completed_at = utcnow()
        call.duration_ms = int((time.monotonic() - started) * 1000)
        outcome.steps.append(
            {
                "id": str(call.id),
                "title": tool.step_title if tool else f"Unknown tool {name}",
                "status": {"completed": "completed", "failed": "failed"}.get(status.value, "completed"),
                "toolName": name,
                "toolInput": call.input,
                "toolOutput": output if output is not None else ({"error": error} if error else None),
                "timestamp": completed_at.isoformat(),
            }
        )

    if tool is None:
        finish(ToolCallStatus.FAILED, error="Unknown tool")
        return _result(tool_use_id, {"error": f"Unknown tool: {name}"}, is_error=True)

    try:
        args = tool.parse(raw_input)
        if not tool.requires_approval:
            with db.begin_nested():  # a failing read must not poison the transaction
                output = tool.run(ctx, args)
            finish(ToolCallStatus.COMPLETED, output)
            return _result(tool_use_id, output)

        proposal = tool.propose(ctx, args)
        approval = Approval(
            user_id=ctx.user.id,
            agent_run_id=run.id,
            tool_call_id=call.id,
            action=tool.name,
            action_label=proposal.action_label,
            title=proposal.title[:300],
            description=proposal.description,
            payload={"args": proposal.payload, "details": proposal.details},
            status=ApprovalStatus.PENDING,
            expires_at=utcnow() + timedelta(hours=get_settings().approval_ttl_hours),
        )
        db.add(approval)
        db.flush()
        outcome.approvals.append(approval)
        pending = {"status": "pending_approval", "approval_id": str(approval.id), "preview": proposal.details}
        finish(ToolCallStatus.WAITING_FOR_APPROVAL, pending)
        return _result(
            tool_use_id,
            {**pending, "note": "Not applied yet. The user will approve or reject this in the app."},
        )
    except ToolInputError as exc:
        finish(ToolCallStatus.FAILED, error=str(exc))
        return _result(tool_use_id, {"error": str(exc)}, is_error=True)
    except Exception:
        logger.exception("Tool failed", extra={"tool": name, "agent_run_id": str(run.id)})
        finish(ToolCallStatus.FAILED, error="Tool failed unexpectedly")
        return _result(tool_use_id, {"error": "The tool failed unexpectedly."}, is_error=True)


def _result(tool_use_id: str, payload: dict, *, is_error: bool = False) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": json.dumps(payload, default=str)}
    if is_error:
        block["is_error"] = True
    return block


def _skip_pending(db: Session, outcome: AgentOutcome) -> None:
    """A failed run must not leave half-explained proposals behind."""
    for approval in outcome.approvals:
        approval.status = ApprovalStatus.CANCELLED
        if approval.tool_call_id and (call := db.get(ToolCall, approval.tool_call_id)):
            call.status = ToolCallStatus.SKIPPED
    outcome.approvals = []
