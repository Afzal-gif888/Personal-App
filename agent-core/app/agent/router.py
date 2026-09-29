"""Request understanding and graph routing.

`understand()` is a deterministic first pass that scopes the run: which domains' tools the LLM is
offered, whether document retrieval is warranted, and whether a planning step is worth it. The
LLM still decides which tools to call; this only keeps the prompt focused and avoids retrieving
documents for unrelated requests.
"""

import re

from app.agent.state import AgentState
from app.schemas.agent import Intent
from app.schemas.tool import ToolDomain

_DOMAIN_KEYWORDS: dict[ToolDomain, tuple[str, ...]] = {
    ToolDomain.TASKS: ("task", "todo", "to-do", "assignment", "homework", "finish", "deadline", "due", "internship", "application"),
    ToolDomain.EVENTS: ("meeting", "event", "calendar", "class", "lecture", "appointment", "interview", "schedule", "exam"),
    ToolDomain.REMINDERS: ("remind", "reminder", "alert me", "notify me"),
    ToolDomain.STUDY: ("study", "revise", "revision", "exam", "subject", "course", "syllabus", "session"),
    ToolDomain.FINANCE: ("bill", "pay", "payment", "expense", "spend", "spent", "budget", "subscription", "budget", "rent", "fee", "₹", "rupee", "installment", "emi"),
    ToolDomain.GOALS: ("goal", "target", "progress", "save ₹", "saving"),
    ToolDomain.DOCUMENTS: ("document", "notes", "pdf", "uploaded", "file", "slides"),
    ToolDomain.MEMORY: ("prefer", "remember that", "from now on", "by default", "my timezone"),
}
# Some domains need neighbours: a study plan must see tasks and the calendar to avoid clashes.
_EXPANSIONS: dict[ToolDomain, tuple[ToolDomain, ...]] = {
    ToolDomain.STUDY: (ToolDomain.TASKS, ToolDomain.EVENTS),
    ToolDomain.REMINDERS: (ToolDomain.TASKS,),
}
# Phrases that ask about everything. "this week" alone does not: "bills due this week" is about bills.
_OVERVIEW = ("take care", "overview", "what should i", "what do i need", "prioriti", "catch me up", "agenda", "my week", "my day")
_DOCUMENT_QUESTION = re.compile(
    r"according to|in my (notes|documents?|pdf|slides)|from my (notes|documents?|pdf|slides)|my uploaded|"
    r"uploaded (notes|documents?|pdf)|based on my (notes|documents?)|(notes|pdf|document|slides) (say|says|explain)"
)
_CHANGE = re.compile(
    r"\b(create|add|make|schedule|set up|book|remind|delete|remove|cancel|mark|update|change|move|reschedule|"
    r"log|record|save|remember|snooze|complete|plan)\b"
)


def understand(request: str) -> Intent:
    text = request.lower()
    domains = [d for d, words in _DOMAIN_KEYWORDS.items() if any(w in text for w in words)]
    overview = any(k in text for k in _OVERVIEW)
    needs_documents = bool(_DOCUMENT_QUESTION.search(text))
    if needs_documents and ToolDomain.DOCUMENTS not in domains:
        domains.append(ToolDomain.DOCUMENTS)
    if overview:
        domains = [d for d in ToolDomain if d not in (ToolDomain.DOCUMENTS, ToolDomain.MEMORY)] + [
            d for d in domains if d in (ToolDomain.DOCUMENTS, ToolDomain.MEMORY)
        ]
    for domain in list(domains):
        for extra in _EXPANSIONS.get(domain, ()):
            if extra not in domains:
                domains.append(extra)
    wants_change = bool(_CHANGE.search(text))
    multi_step = overview or ("plan" in text and ToolDomain.STUDY in domains) or len(
        {d for d in domains if d not in _EXPANSIONS.get(ToolDomain.STUDY, ())}
    ) >= 3
    return Intent(domains=domains, needs_documents=needs_documents, wants_change=wants_change, multi_step=multi_step)


def offered_domains(intent: Intent) -> list[ToolDomain] | None:
    """Domains whose tools the LLM sees. None = all tools (the request didn't clearly scope itself)."""
    return intent.domains or None


# --- conditional edges ---


def after_validate(state: AgentState) -> str:
    return "final_response" if state.error else "load_context"


def after_load_context(state: AgentState) -> str:
    return "final_response" if state.error else "understand_request"


def after_agent(state: AgentState) -> str:
    if state.error or state.stop_reason:
        return "final_response"
    return "execute_tools" if state.pending_tool_calls else "final_response"


def after_observe(state: AgentState) -> str:
    return "final_response" if state.stop_reason else "agent"
