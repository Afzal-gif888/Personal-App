"""LangGraph nodes. Each node reads the state and returns only the fields it changes."""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.runnables import RunnableConfig

from app.agent import prompts, router
from app.agent.state import AgentState, ContextSnapshot
from app.approvals.manager import ApprovalManager
from app.backend.client import BackendClient
from app.backend.exceptions import BackendAuthError, BackendError
from app.config.settings import Settings
from app.llm.base import LLMError, LLMProvider
from app.memory.manager import MemoryManager
from app.rag.pipeline import RagService
from app.schemas.agent import AgentError, ErrorCode, Observation, RunStatus, UserContext
from app.schemas.events import AgentEventType as E
from app.schemas.events import event
from app.schemas.tool import ToolCallRecord, ToolCallRequest, ToolCallStatus, ToolDomain
from app.security import redact
from app.tools.registry import ALL_SCOPES, ToolContext, ToolError, ToolRegistry

logger = logging.getLogger(__name__)

MAX_RESULT_CHARS = 12_000  # per tool result fed back to the model
SNAPSHOT_LIMIT = 5


@dataclass
class RunDeps:
    """Per-run services. Not part of state: they are not serializable and never checkpointed."""

    settings: Settings
    llm: LLMProvider
    registry: ToolRegistry
    approvals: ApprovalManager
    memory: MemoryManager
    rag: RagService | None
    backend: BackendClient
    scopes: frozenset[str] = ALL_SCOPES


def deps(config: RunnableConfig) -> RunDeps:
    found = (config.get("configurable") or {}).get("deps")
    if not isinstance(found, RunDeps):
        raise RuntimeError("RunDeps missing from the run config")
    return found


def _tool_ctx(state: AgentState, d: RunDeps) -> ToolContext:
    assert state.user is not None
    return ToolContext(
        backend=d.backend, user=state.user, today=datetime.fromisoformat(state.context.local_now).date(),
        rag=d.rag, memory=d.memory.long_term, scopes=d.scopes,
    )


def _zone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


# --- validate_input ------------------------------------------------------------------------------


async def validate_input(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    d = deps(config)
    events = [event(E.RUN_STARTED, state.run_id)]
    request = state.request.strip()
    if not request:
        return {"events": events, "error": AgentError(code=ErrorCode.INVALID_REQUEST, message="Please enter a message.")}
    if len(request) > d.settings.max_request_chars:
        return {"events": events, "error": AgentError(
            code=ErrorCode.INVALID_REQUEST, message=f"That message is too long (max {d.settings.max_request_chars} characters).")}
    return {"events": events, "request": request}


# --- load_context --------------------------------------------------------------------------------


async def load_context(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    d = deps(config)
    try:
        me = await d.backend.get_me()
        if state.expected_user_id and state.expected_user_id != me.id:
            # The caller named a different user than the token belongs to: refuse, don't pick one.
            return {"error": AgentError(code=ErrorCode.FORBIDDEN, message="You can't act for that user.")}
        snapshot = await d.memory.load(d.backend, conversation_id=state.conversation_id, history=state.history)
        prefs = snapshot.facts_as_dict()
    except BackendAuthError:
        return {"error": AgentError(code=ErrorCode.UNAUTHORIZED, message="Your session has expired. Please sign in again.")}
    except BackendError as exc:
        return {"error": AgentError(code=ErrorCode.BACKEND_UNAVAILABLE, message="It's Personal is unavailable right now. Please try again.", retryable=exc.retryable)}

    tz_name = str(prefs.get("timezone") or "UTC")
    now = datetime.now(_zone(tz_name))
    user = UserContext(user_id=me.id, name=me.name, timezone=tz_name, preferences=prefs, currency=snapshot.currency)
    history = snapshot.history_messages
    return {
        "user": user,
        "context": ContextSnapshot(local_now=now.isoformat(timespec="minutes"), today=now.date().isoformat(), facts=prefs),
        "messages": [*history, {"role": "user", "content": state.request}],
        "events": [event(E.CONTEXT_LOADED, state.run_id, history_messages=len(history), preferences=len(prefs))],
    }


# --- understand_request --------------------------------------------------------------------------


async def understand_request(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    intent = router.understand(state.request)
    return {
        "intent": intent,
        "events": [event(E.REQUEST_UNDERSTOOD, state.run_id, domains=[x.value for x in intent.domains],
                         needs_documents=intent.needs_documents, multi_step=intent.multi_step)],
    }


# --- gather_context ------------------------------------------------------------------------------


async def _highlights(state: AgentState, d: RunDeps) -> dict[str, list[str]]:
    """A small snapshot for narrowly scoped requests. Broad requests rely on tool calls instead."""
    domains = set(state.intent.domains)
    if not domains or len(domains - {ToolDomain.DOCUMENTS, ToolDomain.MEMORY}) > 2:
        return {}
    today = datetime.fromisoformat(state.context.local_now).date()
    week = today + timedelta(days=7)
    jobs: dict[str, Any] = {}
    if ToolDomain.TASKS in domains:
        jobs["tasks"] = d.backend.list_tasks(status=["pending", "in_progress"], due_to=week, page_size=SNAPSHOT_LIMIT)
    if ToolDomain.EVENTS in domains:
        jobs["events"] = d.backend.list_events(start=today, end=today + timedelta(days=3))
    if ToolDomain.FINANCE in domains:
        jobs["bills"] = d.backend.list_bills(status=["upcoming", "due", "overdue"], due_to=week)
    if ToolDomain.GOALS in domains:
        jobs["goals"] = d.backend.list_goals(status="active")
    results = await asyncio.gather(*jobs.values(), return_exceptions=True)
    out: dict[str, list[str]] = {}
    for name, result in zip(jobs, results, strict=False):
        if isinstance(result, BaseException):
            logger.info("Context snapshot skipped", extra={"section": name, "error": type(result).__name__})
            continue
        items = result.items if hasattr(result, "items") and not isinstance(result, list) else result
        lines = []
        for item in list(items)[:SNAPSHOT_LIMIT]:
            if name == "tasks":
                lines.append(f"{item.title} ({item.priority}, due {item.due_date or 'no date'}) id={item.id}")
            elif name == "events":
                lines.append(f"{item.title} on {item.date} at {item.start_time} ({item.event_type}) id={item.id}")
            elif name == "bills":
                lines.append(f"{item.title}: {item.currency} {item.amount:,.2f} due {item.due_date} ({item.status}) id={item.id}")
            elif name == "goals":
                lines.append(f"{item.title}: {item.progress}% ({item.category}) id={item.id}")
        out[name] = lines
    return out


async def gather_context(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    d = deps(config)
    context = state.context.model_copy(update={"highlights": await _highlights(state, d)})
    update: dict[str, Any] = {"context": context}
    # Retrieval only runs for document questions, never for unrelated requests.
    if state.intent.needs_documents and d.rag is not None and state.user is not None:
        try:
            chunks = await d.rag.search(d.backend, state.user.user_id, state.request)
            update["retrieved_documents"] = chunks
            update["events"] = [event(E.DOCUMENTS_RETRIEVED, state.run_id, chunks=len(chunks),
                                      documents=sorted({c.document_name for c in chunks}))]
        except (BackendError, ValueError) as exc:
            logger.warning("Document retrieval failed", extra={"error": type(exc).__name__})
            update["metadata"] = {**state.metadata, "rag_error": "Document search was unavailable for this request."}
    return update


# --- plan ----------------------------------------------------------------------------------------

_STEP = re.compile(r"^\s*(?:\d+[.)]|[-*])\s*(.+)$")


async def plan(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    d = deps(config)
    events = [event(E.PLANNING_STARTED, state.run_id, multi_step=state.intent.multi_step)]
    steps = ["Answer the request using the relevant tools"]
    if state.intent.multi_step and d.settings.llm_planning:
        try:
            result = await d.llm.invoke(
                system=prompts.build_plan_prompt(state),
                messages=[{"role": "user", "content": state.request}], tools=[], purpose="plan",
            )
            parsed = [m.group(1).strip() for line in result.text.splitlines() if (m := _STEP.match(line))]
            steps = parsed[:8] or steps
        except LLMError as exc:  # planning is an aid, not a requirement
            logger.info("Planning skipped", extra={"error": exc.message})
    events.append(event(E.PLAN_CREATED, state.run_id, steps=len(steps)))
    return {"plan": steps, "events": events}


# --- agent ---------------------------------------------------------------------------------------


async def agent(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    d = deps(config)
    if state.iterations >= d.settings.max_agent_iterations:
        return {"stop_reason": "iteration_limit", "pending_tool_calls": []}
    specs = d.registry.specs(router.offered_domains(state.intent))
    try:
        result = await d.llm.invoke(system=prompts.build_system_prompt(state), messages=state.messages, tools=specs)
    except LLMError as exc:
        code = ErrorCode.RATE_LIMITED if exc.rate_limited else ErrorCode.LLM_ERROR
        return {"error": AgentError(code=code, message=exc.message, retryable=exc.retryable), "pending_tool_calls": []}

    update: dict[str, Any] = {
        "messages": [{"role": "assistant", "content": result.content}],
        "iterations": state.iterations + 1,
        "metadata": {**state.metadata, "model": result.model},
    }
    if result.stop_reason == "refusal":
        return update | {"stop_reason": "refusal", "pending_tool_calls": []}
    calls = result.tool_calls
    if calls and state.tool_call_count + len(calls) > d.settings.max_tool_calls:
        return update | {"stop_reason": "tool_limit", "pending_tool_calls": []}
    return update | {"pending_tool_calls": calls}


# --- execute_tools -------------------------------------------------------------------------------


def _result_block(call_id: str, payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(payload, default=str)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + ' …"}'  # keep the model's context bounded
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": call_id, "content": text}
    if is_error:
        block["is_error"] = True
    return block


async def _run_one(state: AgentState, d: RunDeps, call: ToolCallRequest, ctx: ToolContext) -> tuple[dict, ToolCallRecord, list]:
    started = time.monotonic()
    events = [event(E.TOOL_STARTED, state.run_id, tool=call.name, tool_call_id=call.id)]
    safe_input = redact(call.input)

    def record(status: ToolCallStatus, **kw: Any) -> ToolCallRecord:
        return ToolCallRecord(id=call.id, name=call.name, input=safe_input, status=status,
                              duration_ms=int((time.monotonic() - started) * 1000), **kw)

    tool = d.registry.get(call.name)
    if tool is None:
        msg = f"Unknown tool {call.name}"
        events.append(event(E.TOOL_FAILED, state.run_id, tool=call.name, error=msg))
        return _result_block(call.id, {"error": msg}, is_error=True), record(ToolCallStatus.FAILED, error=msg), events
    try:
        args = tool.parse(call.input)
        if tool.requires_approval(d.settings.mutation_policy):
            assert state.user is not None
            approval = await d.approvals.request(
                user_id=state.user.user_id, run_id=state.run_id, tool=tool, tool_call_id=call.id,
                payload=args.model_dump(mode="json", exclude_none=True),
            )
            events.append(event(E.APPROVAL_REQUIRED, state.run_id, tool=call.name, approval_id=approval.id))
            payload = {"status": "approval_required", "approval_id": approval.id,
                       "message": "Not done yet: this action is waiting for the user's approval."}
            rec = record(ToolCallStatus.APPROVAL_REQUIRED, approval_id=approval.id)
            return _result_block(call.id, payload), rec, events + [approval.to_request()]
        output = await d.registry.execute(tool, args, ctx)
    except ToolError as exc:
        events.append(event(E.TOOL_FAILED, state.run_id, tool=call.name, error=str(exc)))
        return _result_block(call.id, {"error": str(exc)}, is_error=True), record(ToolCallStatus.FAILED, error=str(exc)), events
    except Exception:  # a bug in a tool must not take down the run or leak a stack trace
        logger.exception("Tool crashed", extra={"tool": call.name})
        msg = "The tool failed unexpectedly."
        events.append(event(E.TOOL_FAILED, state.run_id, tool=call.name, error=msg))
        return _result_block(call.id, {"error": msg}, is_error=True), record(ToolCallStatus.FAILED, error=msg), events
    events.append(event(E.TOOL_COMPLETED, state.run_id, tool=call.name, duration_ms=int((time.monotonic() - started) * 1000)))
    return _result_block(call.id, output), record(ToolCallStatus.COMPLETED, output=redact(output)), events


async def execute_tools(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    d = deps(config)
    ctx = _tool_ctx(state, d)
    outcomes = await asyncio.gather(*(_run_one(state, d, call, ctx) for call in state.pending_tool_calls))
    blocks, records, events, approvals = [], [], [], []
    for block, rec, evts in outcomes:
        blocks.append(block)
        records.append(rec)
        for item in evts:
            (events if hasattr(item, "type") else approvals).append(item)
    return {
        # All results for one assistant turn go back in a single user message.
        "messages": [{"role": "user", "content": blocks}],
        "tool_calls": records,
        "events": events,
        "pending_approvals": approvals,
        "tool_call_count": state.tool_call_count + len(records),
        "pending_tool_calls": [],
    }


# --- observe -------------------------------------------------------------------------------------


def _summarize(rec: ToolCallRecord) -> str:
    if rec.status == ToolCallStatus.APPROVAL_REQUIRED:
        return "waiting for approval"
    if rec.status == ToolCallStatus.FAILED:
        return f"failed: {rec.error}"
    out = rec.output or {}
    if "items" in out:
        return f"{len(out['items'])} item(s)"
    if "chunks" in out:
        return f"{len(out['chunks'])} relevant passage(s)"
    return str(out.get("summary") or out.get("title") or out.get("name") or "done")


async def observe(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    d = deps(config)
    new = state.tool_calls[-_last_batch_size(state):] if state.tool_calls else []
    observations = [Observation(tool_call_id=r.id, tool_name=r.name, ok=r.status != ToolCallStatus.FAILED, summary=_summarize(r)) for r in new]
    update: dict[str, Any] = {"observations": observations}
    retrieved = [c for r in new if r.name == "search_documents" and r.output for c in r.output.get("chunks", [])]
    if retrieved:
        from app.rag.schemas import RetrievedChunk

        known = {c.chunk_id for c in state.retrieved_documents}
        update["retrieved_documents"] = [RetrievedChunk.model_validate(c) for c in retrieved if c["chunk_id"] not in known]
    if state.iterations >= d.settings.max_agent_iterations:
        update["stop_reason"] = "iteration_limit"
    return update


def _last_batch_size(state: AgentState) -> int:
    last = state.messages[-1] if state.messages else {}
    content = last.get("content")
    return sum(1 for b in content if b.get("type") == "tool_result") if isinstance(content, list) else 0


# --- final_response ------------------------------------------------------------------------------

_LIMIT_NOTES = {
    "iteration_limit": (ErrorCode.ITERATION_LIMIT, "I stopped because this request needed more steps than I'm allowed in one go."),
    "tool_limit": (ErrorCode.TOOL_LIMIT, "I stopped because this request needed more tool calls than I'm allowed in one go."),
}


def _last_assistant_text(state: AgentState) -> str:
    for message in reversed(state.messages):
        if message.get("role") == "assistant":
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            text = "\n\n".join(b.get("text", "") for b in content or [] if b.get("type") == "text").strip()
            if text:
                return text
    return ""


async def final_response(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    if state.error:
        return {"status": RunStatus.FAILED, "final_response": state.error.message,
                "events": [event(E.RUN_FAILED, state.run_id, code=state.error.code.value)]}

    events = []
    text = _last_assistant_text(state) if not state.pending_tool_calls else ""
    status = RunStatus.COMPLETED
    error = None
    if state.stop_reason == "refusal":
        text = "Sorry, I can't help with that request."
    elif state.stop_reason in _LIMIT_NOTES:
        code, note = _LIMIT_NOTES[state.stop_reason]
        status, error = RunStatus.INCOMPLETE, AgentError(code=code, message=note)
        done = [o for o in state.observations if o.ok]
        text = note
        if done:
            text += "\n\nWhat I got done:\n" + "\n".join(f"- {o.tool_name}: {o.summary}" for o in done[-8:])
        text += "\n\nTry asking for one part at a time."
        events.append(event(E.LIMIT_REACHED, state.run_id, reason=state.stop_reason, iterations=state.iterations,
                            tool_calls=state.tool_call_count))
    if state.pending_approvals and status == RunStatus.COMPLETED:
        status = RunStatus.APPROVAL_REQUIRED
    if not text:
        text = "Done." if status != RunStatus.APPROVAL_REQUIRED else "This needs your approval before I go ahead."
    events.append(event(E.RUN_COMPLETED, state.run_id, status=status.value, iterations=state.iterations,
                        tool_calls=state.tool_call_count))
    update: dict[str, Any] = {"status": status, "final_response": text, "events": events}
    if error:
        update["error"] = error
    return update
