"""Deterministic test double for the LLM. Test-only: the application never falls back to it."""

import json
import re
from collections import deque
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from app.llm.base import LLMError, LLMProvider, LLMResult, LLMToolSpec, Purpose

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_TODAY = re.compile(r"Today is (\d{4}-\d{2}-\d{2})")
_TIME = re.compile(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
_AMOUNT = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(?:rupees|inr)", re.IGNORECASE)
_PERCENT = re.compile(r"(\d{1,3})\s*%")


def _text_of(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content or [] if b.get("type") == "text")


def _is_user_text(message: dict[str, Any]) -> bool:
    if message.get("role") != "user":
        return False
    content = message.get("content")
    return isinstance(content, str) or any(b.get("type") == "text" for b in content or [])


def _tool_results(messages: Iterable[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """(tool_name, parsed output) for every tool result, matched to its tool_use by id."""
    names: dict[str, str] = {}
    out: list[tuple[str, dict[str, Any]]] = []
    for m in messages:
        content = m.get("content")
        for b in content if isinstance(content, list) else []:
            if b.get("type") == "tool_use":
                names[b["id"]] = b["name"]
            elif b.get("type") == "tool_result":
                try:
                    payload = json.loads(b.get("content") or "{}")
                except (TypeError, ValueError):
                    payload = {"raw": b.get("content")}
                out.append((names.get(b.get("tool_use_id", ""), "tool"), payload))
    return out


class MockLLMProvider(LLMProvider):
    """Deterministic, keyless stand-in for a real model.

    Two modes:
    * scripted - pass `responses`; each `invoke` pops the next `LLMResult` (for precise tests).
    * heuristic - keyword rules pick tools the way a model would, over one or more rounds, and the
      final answer summarises the tool results. Same tools, same approval flow, no API key.
    """

    name = "mock"
    model = "mock-agent-1"

    def __init__(self, responses: Iterable[LLMResult] | None = None) -> None:
        self._scripted: deque[LLMResult] | None = deque(responses) if responses is not None else None
        self.calls: list[dict[str, Any]] = []
        self._ids = 0

    async def invoke(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[LLMToolSpec], purpose: Purpose = "act"
    ) -> LLMResult:
        self.calls.append({"purpose": purpose, "tools": [t.name for t in tools], "messages": len(messages), "system": system})
        # Like the real model is told to: don't search again when the documents were already searched.
        self._already_searched = "## Relevant document excerpts" in system or "## Document search" in system
        if self._scripted is not None:
            if not self._scripted:
                raise LLMError("The mock provider has no scripted responses left.")
            return self._scripted.popleft()
        m = _TODAY.search(system)
        today = date.fromisoformat(m.group(1)) if m else date.today()
        request_idx = max((i for i, msg in enumerate(messages) if _is_user_text(msg)), default=-1)
        request = _text_of(messages[request_idx]) if request_idx >= 0 else ""
        turn = messages[request_idx + 1 :]
        if purpose == "plan":
            return self._text(self._plan(request))
        rounds_done = sum(
            1 for msg in turn if msg.get("role") == "assistant" and any(b.get("type") == "tool_use" for b in msg.get("content") or [])
        )
        results = _tool_results(turn)
        available = {t.name for t in tools}
        calls = [c for c in self._next_calls(request.lower(), request, rounds_done, results, today) if c[0] in available]
        if calls:
            return self._tool_use(calls)
        return self._text(self._answer(request, results, system))

    # -- building results --

    def _next_id(self) -> str:
        self._ids += 1
        return f"toolu_mock_{self._ids}"

    def _tool_use(self, calls: list[tuple[str, dict[str, Any]]]) -> LLMResult:
        blocks = [{"type": "text", "text": "Let me check that."}]
        blocks += [{"type": "tool_use", "id": self._next_id(), "name": n, "input": i} for n, i in calls]
        return LLMResult(content=blocks, stop_reason="tool_use", model=self.model)

    def _text(self, text: str) -> LLMResult:
        return LLMResult(content=[{"type": "text", "text": text}], stop_reason="end_turn", model=self.model)

    # -- heuristics --

    @staticmethod
    def _plan(request: str) -> str:
        text = request.lower()
        steps = ["Understand what the student needs"]
        if "study plan" in text or "exam" in text:
            steps += ["Look up subjects, open tasks and the existing schedule", "Draft study sessions before the exam"]
        if "week" in text:
            steps += ["Collect tasks, events, bills, reminders and goals for the week", "Prioritise by deadline"]
        steps.append("Summarise the result clearly")
        return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))

    def _next_calls(
        self, text: str, original: str, round_: int, results: list[tuple[str, dict[str, Any]]], today: date
    ) -> list[tuple[str, dict[str, Any]]]:
        week_end = (today + timedelta(days=7)).isoformat()

        if any(k in text for k in ("according to", "my notes", "uploaded", "document", "pdf")):
            if getattr(self, "_already_searched", False):
                return []
            return [("search_documents", {"query": original})] if round_ == 0 else []

        if "remind me" in text:
            if round_:
                return []
            title = re.split(r"\b(?:tomorrow|today|tonight|at \d|every|on (?:mon|tue|wed|thu|fri|sat|sun))", text.split("remind me", 1)[1])[0]
            title = re.sub(r"^\s*(to|about)\s+", "", title).strip(" .") or "Reminder"
            repeat = "weekly" if "every" in text and any(d in text for d in _WEEKDAYS) else "daily" if "every day" in text else "none"
            return [("create_reminder", {
                "title": title[:1].upper() + title[1:], "date": _date_in(text, today).isoformat(),
                "time": _time_in(text) or "09:00", "repeat_rule": repeat,
            })]

        if ("study plan" in text) or ("exam" in text and "plan" in text):
            if round_ == 0:
                return [
                    ("get_subjects", {}),
                    ("get_tasks", {"status": "open", "limit": 20}),
                    ("get_events", {"start_date": today.isoformat(), "end_date": _date_in(text, today, default_days=7).isoformat()}),
                ]
            if round_ == 1:
                subject = _subject_in(original, results)
                exam = _date_in(text, today, default_days=7)
                days = max(1, min(14, (exam - today).days - 1 or 1))
                return [("create_study_plan", {"subject": subject, "days": days,
                                               "start_date": (today + timedelta(days=1)).isoformat()})]
            return []

        if "delete" in text and "task" in text:
            if round_ == 0:
                return [("get_tasks", {"query": _object_after(text, ("delete", "my", "the", "task")), "status": "all"})]
            if round_ == 1:
                ids = _matching_ids(results, "get_tasks", text)
                return [("delete_task", {"task_id": ids[0]})] if ids else []
            return []

        if ("mark" in text or "complete" in text) and ("completed" in text or "done" in text or "complete" in text):
            if round_ == 0:
                name = re.sub(r"\b(mark|my|the|as|completed|complete|done)\b", " ", text)
                return [("get_tasks", {"query": " ".join(name.split())[:60], "status": "open"})]
            if round_ == 1:
                ids = _matching_ids(results, "get_tasks", text)
                return [("complete_task", {"task_id": ids[0]})] if ids else []
            return []

        if ("task" in text) and any(k in text for k in ("create", "add", "new task", "task to")):
            if round_:
                return []
            title = re.split(r"task (?:to|for)\s+", text, maxsplit=1)[-1]
            title = re.split(r"\b(?:tomorrow|today|by|on|due)\b", title)[0].strip(" .") or "New task"
            category = "academic" if any(k in text for k in ("assignment", "exam", "lab", "study", "homework")) else "general"
            args: dict[str, Any] = {"title": title[:1].upper() + title[1:], "category": category}
            if any(k in text for k in ("tomorrow", "today", "next ", *_WEEKDAYS)):
                args["due_date"] = _date_in(text, today).isoformat()
            return [("create_task", args)]

        if "meeting" in text and any(k in text for k in ("create", "schedule", "add", "set up", "book")):
            if round_:
                return []
            kind = "project_meeting" if "project" in text else "meeting"
            return [("create_event", {
                "title": "Project meeting" if kind == "project_meeting" else "Meeting", "event_type": kind,
                "date": _date_in(text, today).isoformat(), "start_time": _time_in(text) or "10:00",
            })]

        if "bill" in text and any(k in text for k in ("add", "create", "new")):
            if round_:
                return []
            amount = _amount_in(original) or 0
            category = next((c for c in ("electricity", "internet", "phone", "rent") if c in text), "other")
            return [("create_bill", {"title": f"{category.title()} bill" if category != "other" else "Bill",
                                      "amount": amount, "category": category,
                                      "due_date": _date_in(text, today).isoformat()})]

        if "goal" in text and any(k in text for k in ("create", "new goal", "set a goal", "goal to")):
            if round_:
                return []
            amount = _amount_in(original)
            title = re.split(r"goal (?:to|of)\s+", text, maxsplit=1)[-1].strip(" .") or "New goal"
            args = {"title": title[:1].upper() + title[1:], "category": "financial" if amount else "personal"}
            if amount:
                args |= {"target_value": amount, "unit": "INR"}
            return [("create_goal", args)]

        if "goal" in text and _PERCENT.search(text):
            if round_ == 0:
                return [("get_goals", {"status": "active"})]
            if round_ == 1:
                ids = _matching_ids(results, "get_goals", text)
                pct = int(_PERCENT.search(text).group(1))  # type: ignore[union-attr]
                return [("update_goal_progress", {"goal_id": ids[0], "progress": min(pct, 100)})] if ids else []
            return []

        if any(k in text for k in ("take care", "overview", "what should i", "what do i need", "my week")):
            if round_:
                return []
            return [
                ("get_tasks", {"status": "open", "due_within_days": 7}),
                ("get_events", {"start_date": today.isoformat(), "end_date": week_end}),
                ("get_bills", {"due_within_days": 7}),
                ("get_reminders", {"status": "pending"}),
                ("get_goals", {"status": "active"}),
            ]

        if round_:
            return []
        if "bill" in text:
            return [("get_bills", {"due_within_days": 7} if "week" in text else {})]
        if "spend" in text or "spent" in text or "expense" in text:
            return [("get_expense_summary", {})]
        if "subscription" in text:
            return [("get_subscriptions", {"status": "active"})]
        if "goal" in text:
            return [("get_goals", {"status": "active"})]
        if "reminder" in text:
            return [("get_reminders", {"status": "pending"})]
        if "meeting" in text or "event" in text or "calendar" in text:
            return [("get_events", {"start_date": today.isoformat(), "end_date": week_end})]
        if "task" in text or "assignment" in text:
            args = {"status": "open"}
            if "high" in text:
                args["priority"] = "high"
            return [("get_tasks", args)]
        if "prefer" in text and "study" in text:
            start = _time_in(text)
            return [("remember_preference", {"key": "preferred_study_start", "value": start})] if start else []
        return []

    @staticmethod
    def _answer(request: str, results: list[tuple[str, dict[str, Any]]], system: str) -> str:
        if not results:
            if "Relevant document excerpts" in system:
                return "Based on your documents: " + system.split("Relevant document excerpts", 1)[1][:300].strip()
            return "I can help with your tasks, schedule, reminders, study plans, finances, goals and documents. What would you like to do?"
        lines: list[str] = []
        for tool, payload in results:
            if payload.get("status") == "approval_required":
                lines.append(f"- {tool}: waiting for your approval before I make this change.")
            elif payload.get("error"):
                lines.append(f"- {tool}: couldn't complete ({payload['error']}).")
            elif "chunks" in payload:
                chunks = payload["chunks"]
                if chunks:
                    c = chunks[0]
                    lines.append(f"According to {c.get('document_name', 'your document')}: {c.get('text', '')[:280]}")
                else:
                    lines.append("I couldn't find anything relevant in your documents.")
            elif "items" in payload:
                items = payload["items"]
                names = ", ".join(str(i.get("title") or i.get("name") or i.get("topic") or "") for i in items[:5])
                lines.append(f"- {tool}: {len(items)} found" + (f" ({names})" if names else ""))
            else:
                label = payload.get("title") or payload.get("name") or payload.get("summary") or "done"
                lines.append(f"- {tool}: {label}")
        return "Here's what I found:\n" + "\n".join(lines)


# -- tiny parsers used by the mock --


def _date_in(text: str, today: date, *, default_days: int = 0) -> date:
    if "tomorrow" in text:
        return today + timedelta(days=1)
    if "today" in text or "tonight" in text:
        return today
    for i, name in enumerate(_WEEKDAYS):
        if name in text:
            ahead = (i - today.weekday()) % 7 or 7
            if f"next {name}" in text and ahead < 7:
                ahead += 7 if today.weekday() >= i else 0
            return today + timedelta(days=ahead)
    return today + timedelta(days=default_days)


def _time_in(text: str) -> str | None:
    m = _TIME.search(text)
    if not m:
        return None
    hour, minute, ampm = int(m.group(1)) % 12, int(m.group(2) or 0), m.group(3).lower()
    return f"{hour + (12 if ampm == 'pm' else 0):02d}:{minute:02d}"


def _amount_in(text: str) -> float | None:
    m = _AMOUNT.search(text)
    if not m:
        return None
    return float((m.group(1) or m.group(2)).replace(",", ""))


def _object_after(text: str, stop: tuple[str, ...]) -> str:
    return " ".join(w for w in re.findall(r"[a-z0-9]+", text) if w not in stop)[:60]


def _first_ids(results: list[tuple[str, dict[str, Any]]], tool: str) -> list[str]:
    for name, payload in results:
        if name == tool:
            return [i["id"] for i in payload.get("items", []) if i.get("id")]
    return []


def _matching_ids(results: list[tuple[str, dict[str, Any]]], tool: str, text: str) -> list[str]:
    for name, payload in results:
        if name == tool:
            items = payload.get("items", [])
            words = set(re.findall(r"[a-z]{4,}", text))
            ranked = sorted(items, key=lambda i: -len(words & set(re.findall(r"[a-z]{4,}", str(i.get("title", "")).lower()))))
            return [i["id"] for i in ranked if i.get("id")]
    return []


def _subject_in(request: str, results: list[tuple[str, dict[str, Any]]]) -> str:
    lowered = request.lower()
    for name, payload in results:
        if name == "get_subjects":
            for subj in payload.get("items", []):
                for key in (subj.get("name"), subj.get("code")):
                    if key and key.lower() in lowered:
                        return subj["name"]
    m = re.search(r"\b(?:an?|my)\s+([A-Za-z0-9+#]{2,20})\s+exam", request)
    return m.group(1) if m else "General"
