"""Deterministic test double for a real model. Test-only: the application never falls back to it.

It speaks the same protocol as the real provider: it reads the transcript, emits tool_use blocks,
and writes a final answer from the tool results. Intent is picked from keywords in the request.
"""

import json
import re
import uuid
from datetime import date, timedelta
from typing import Any

from app.llm import LLMResponse, ToolSpec

_TODAY = re.compile(r"Today is (\d{4}-\d{2}-\d{2})")
_TIME = re.compile(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.IGNORECASE)
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_SUBJECT = re.compile(
    r"\b(?:for|on)\s+(?:my\s+|the\s+)?([a-z][\w&+\- ]{1,40}?)(?:\s+(?:exam|test|midterm|final|quiz)s?\b|[.?!,]|$)",
    re.IGNORECASE,
)


class MockProvider:
    name = "mock"

    def complete(self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> LLMResponse:
        match = _TODAY.search(system)
        today = date.fromisoformat(match.group(1)) if match else date.today()
        request, rounds = _current_turn(messages)
        text = request.lower()

        for keywords, handler in _INTENTS:
            if any(k in text for k in keywords):
                result = handler(request, text, today, rounds)
                break
        else:
            result = (
                "I can help you plan study sessions, set reminders, add tasks, check your calendar, "
                "review bills and spending, and track goals. What would you like to do?"
            )
        if isinstance(result, str):
            return LLMResponse(content=[{"type": "text", "text": result}], stop_reason="end_turn", model="mock")
        return LLMResponse(
            content=[
                {"type": "tool_use", "id": f"toolu_{uuid.uuid4().hex[:20]}", "name": name, "input": args}
                for name, args in result
            ],
            stop_reason="tool_use",
            model="mock",
        )


# --- Transcript parsing ---------------------------------------------------------------------------


def _current_turn(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """The latest user request and, per completed tool round since then, {tool_name: result}."""
    start = max(i for i, m in enumerate(messages) if m["role"] == "user" and isinstance(m["content"], str))
    request = messages[start]["content"]
    names: dict[str, str] = {}
    rounds: list[dict[str, Any]] = []
    for msg in messages[start + 1 :]:
        blocks = msg["content"] if isinstance(msg["content"], list) else []
        if msg["role"] == "assistant":
            names.update({b["id"]: b["name"] for b in blocks if b.get("type") == "tool_use"})
        else:
            round_results = {}
            for b in blocks:
                if b.get("type") == "tool_result":
                    try:
                        round_results[names.get(b["tool_use_id"], "?")] = json.loads(b["content"])
                    except (TypeError, ValueError):
                        round_results[names.get(b["tool_use_id"], "?")] = {"error": str(b.get("content"))}
            rounds.append(round_results)
    return request, rounds


def _parse_day(text: str, today: date) -> date:
    if "today" in text or "tonight" in text:
        return today
    for i, name in enumerate(_WEEKDAYS):
        if name in text:
            return today + timedelta(days=(i - today.weekday() - 1) % 7 + 1)
    return today + timedelta(days=1)


def _parse_time(text: str, default: str) -> str:
    m = _TIME.search(text)
    if not m:
        return default
    hour, minute, meridiem = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return default
    return f"{hour:02d}:{minute:02d}"


def _errors(results: dict[str, Any]) -> list[str]:
    return [r["error"] for r in results.values() if isinstance(r, dict) and "error" in r]


def _approval_note(results: dict[str, Any]) -> str | None:
    errors = _errors(results)
    if errors:
        return "I couldn't draft that: " + errors[0]
    if any(isinstance(r, dict) and r.get("status") == "pending_approval" for r in results.values()):
        return "It's waiting for your approval, so nothing has changed yet."
    return None


def _money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


# --- Intents --------------------------------------------------------------------------------------


def _study_plan(request, text, today, rounds):
    if not rounds:
        return [("list_calendar", {"start_date": today.isoformat(), "end_date": (today + timedelta(days=7)).isoformat()})]
    if len(rounds) == 1:
        m = _SUBJECT.search(request)
        subject = m.group(1).strip().title() if m else "General revision"
        return [("create_study_plan", {"subject": subject, "days": 4, "minutes_per_day": 90, "session_minutes": 45})]
    plan = rounds[-1].get("create_study_plan", {})
    if "error" in plan:
        return f"I couldn't build a plan: {plan['error']}"
    preview = plan.get("preview", {})
    lines = "\n".join(f"• {s}" for s in preview.get("Schedule", [])[:8])
    return (
        f"I checked your calendar and drafted a {preview.get('Sessions')}-session plan "
        f"({preview.get('Total hours')} hours) for {preview.get('Subject')}:\n\n{lines}\n\n"
        + (_approval_note(rounds[-1]) or "")
    )


def _bills(request, text, today, rounds):
    if not rounds:
        return [("list_bills", {"due_within_days": 14})]
    bills = rounds[0].get("list_bills", {}).get("bills", [])
    if not bills:
        return "You have no unpaid bills due in the next two weeks."
    listing = "\n".join(
        f"• {b['title']}: {_money(b['amount'], b['currency'])} (due {b['due_date']}, {b['status']})" for b in bills
    )
    if len(rounds) == 1:
        first = bills[0]
        due = date.fromisoformat(first["due_date"])
        remind_on = max(today, due - timedelta(days=1))
        return [
            (
                "create_reminder",
                {
                    "title": f"Pay {first['title']} ({_money(first['amount'], first['currency'])})",
                    "date": remind_on.isoformat(),
                    "time": "10:00",
                    "category": "financial",
                },
            )
        ]
    return (
        f"Here are your unpaid bills for the next two weeks:\n\n{listing}\n\n"
        f"I drafted a reminder for the earliest one. " + (_approval_note(rounds[-1]) or "")
    )


def _expenses(request, text, today, rounds):
    if not rounds:
        return [("summarize_expenses", {})]
    s = rounds[0].get("summarize_expenses", {})
    if "error" in s:
        return f"I couldn't summarise your spending: {s['error']}"
    if not s.get("count"):
        return f"You haven't logged any expenses for {s.get('month')} yet."
    cats = "\n".join(
        f"• {c['category'].title()}: {_money(c['total'], s['currency'])}" for c in s.get("by_category", [])
    )
    return f"Spending for {s['month']}:\n\n{cats}\n\nTotal: {_money(s['total'], s['currency'])} across {s['count']} expenses."


_BUDGET_CATEGORIES = ("food", "travel", "education", "shopping", "bills", "entertainment", "health", "other")


def _budgets(request, text, today, rounds):
    amount = re.search(r"(\d[\d,]*(?:\.\d{1,2})?)", text)
    if amount and any(k in text for k in ("set", "limit", "make", "change", "create")):
        # "Set my food budget to 3000"
        if not rounds:
            args = {"amount": amount.group(1).replace(",", "")}
            category = next((c for c in _BUDGET_CATEGORIES if c in text), None)
            if category:
                args["category"] = category
            return [("set_budget", args)]
        note = _approval_note(rounds[0])
        if note and note.startswith("I couldn't"):
            return note
        return f"I drafted that budget. {note or ''}".strip()
    if not rounds:
        return [("get_budget_status", {})]
    b = rounds[0].get("get_budget_status", {})
    if "error" in b:
        return f"I couldn't check your budgets: {b['error']}"
    items = b.get("budgets", [])
    if not items:
        return "You haven't set any budgets yet. Try “Set my food budget to 3000”."
    flag = {"on_track": "", "warning": " (close to the limit)", "over": " (over budget)"}
    lines = "\n".join(
        f"• {(i['category'] or 'Overall').title()}: {_money(i['spent'], i['currency'])} of "
        f"{_money(i['limit'], i['currency'])}, {i['percent_used']}%{flag[i['status']]}"
        for i in items
    )
    return f"Budgets for {b['month']}:\n\n{lines}"


def _goals(request, text, today, rounds):
    if not rounds:
        return [("list_goals", {})]
    goals = rounds[0].get("list_goals", {}).get("goals", [])
    if not goals:
        return "You don't have any active goals yet. Want to set one?"
    lines = "\n".join(
        f"• {g['title']}: {g['progress']}%" + (f" (deadline {g['deadline']})" if g.get("deadline") else "")
        for g in goals
    )
    return f"Your active goals:\n\n{lines}"


def _reminder(request, text, today, rounds):
    if not rounds:
        m = re.search(r"remind me (?:to |about )?(.+)", request, re.IGNORECASE)
        title = m.group(1) if m else request
        title = re.split(r"\s+(?:at \d|tomorrow|today|tonight|on (?:mon|tue|wed|thu|fri|sat|sun))", title, flags=re.I)[0]
        title = title.strip(" .!?") or "Reminder"
        return [
            (
                "create_reminder",
                {
                    "title": title[:1].upper() + title[1:],
                    "date": _parse_day(text, today).isoformat(),
                    "time": _parse_time(request, "09:00"),
                },
            )
        ]
    result = rounds[0].get("create_reminder", {})
    if "error" in result:
        return f"I couldn't draft that reminder: {result['error']}"
    p = result.get("preview", {})
    return f"I drafted a reminder “{p.get('Title')}” for {p.get('Date')} at {p.get('Time')}. " + (
        _approval_note(rounds[0]) or ""
    )


def _task(request, text, today, rounds):
    if not rounds:
        m = re.search(r"(?:add|create|new)\s+(?:a\s+)?(?:task|todo|to-do)(?:\s+to)?[:\s]+(.+)", request, re.IGNORECASE)
        title = (m.group(1) if m else request).strip(" .!?")
        args = {"title": title[:1].upper() + title[1:], "priority": "high" if "urgent" in text else "medium"}
        if any(k in text for k in ("today", "tomorrow", *_WEEKDAYS)):
            args["due_date"] = _parse_day(text, today).isoformat()
        return [("create_task", args)]
    return "I drafted that task. " + (_approval_note(rounds[0]) or "")


def _schedule(request, text, today, rounds):
    if not rounds:
        return [
            ("list_calendar", {"start_date": today.isoformat(), "end_date": (today + timedelta(days=6)).isoformat()}),
            ("list_tasks", {"due_within_days": 7}),
        ]
    cal, tasks = rounds[0].get("list_calendar", {}), rounds[0].get("list_tasks", {})
    items = [f"• {e['start'][:16].replace('T', ' ')} {e['title']}" for e in cal.get("events", [])]
    items += [f"• {s['date']} {s['start_time']} Study: {s['topic']}" for s in cal.get("study_sessions", [])]
    due = [f"• {t['title']}" + (f" (due {t['due_date']})" if t.get("due_date") else "") for t in tasks.get("tasks", [])]
    parts = ["Your next 7 days:\n\n" + ("\n".join(sorted(items)) if items else "Nothing scheduled.")]
    if due:
        parts.append("Tasks due:\n\n" + "\n".join(due))
    return "\n\n".join(parts)


_INTENTS = [
    (("study plan", "exam", "revise", "revision", "prepare for"), _study_plan),
    (("remind",), _reminder),
    (("bill", "electricity", "internet", "rent", "pay "), _bills),
    (("budget",), _budgets),
    (("expense", "spent", "spending"), _expenses),
    (("goal", "progress"), _goals),
    (("add a task", "add task", "create a task", "new task", "todo", "to-do"), _task),
    (("schedule", "calendar", "this week", "today", "upcoming"), _schedule),
]
