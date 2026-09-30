"""Every tool, run on its own against the fake backend (no agent, no LLM)."""

from datetime import timedelta

import pytest

from app.schemas.tool import ToolRisk
from app.tools.registry import ToolError, ToolInputError, ToolPermissionError
from tests.fakes import USER_A, USER_B


def ids(h, kind):
    return [x["id"] for x in h.fake.data[USER_A][kind]]


async def run(h, ctx, name, args):
    tool = h.services.registry.get(name)
    assert tool is not None, name
    return await h.services.registry.execute(tool, tool.parse(args), ctx)


def test_registry_covers_every_required_tool(harness):
    required = {
        "get_tasks", "get_task", "create_task", "update_task", "complete_task", "delete_task",
        "get_events", "create_event", "update_event", "delete_event",
        "get_reminders", "create_reminder", "complete_reminder", "snooze_reminder", "cancel_reminder",
        "get_subjects", "get_study_plan", "create_study_plan", "update_study_plan", "create_study_session", "complete_study_session",
        "get_bills", "create_bill", "update_bill", "mark_bill_paid", "get_payments", "get_payment_plans", "create_payment_plan",
        "get_expenses", "create_expense", "get_subscriptions", "create_subscription",
        "get_goals", "create_goal", "update_goal", "update_goal_progress",
        "get_documents", "search_documents", "get_document",
    }
    assert required <= set(harness.services.registry.names)


def test_every_tool_declares_schemas_risk_and_permission(harness):
    for tool in harness.services.registry.tools():
        spec = tool.spec()
        assert spec.description and spec.input_schema["type"] == "object"
        assert tool.output_model.model_json_schema()
        assert tool.risk in ToolRisk
        assert tool.permission.endswith((":read", ":write"))
        # The LLM sees snake_case field names; camelCase is only for the backend.
        assert all("_" in k or k.islower() for k in spec.input_schema.get("properties", {}))


def test_risk_policy(harness):
    reg = harness.services.registry
    assert reg.get("get_tasks").risk == ToolRisk.READ
    assert reg.get("create_task").risk == ToolRisk.MUTATE
    assert reg.get("delete_task").risk == ToolRisk.CONSEQUENTIAL
    assert reg.get("delete_event").requires_approval("direct")
    assert not reg.get("create_reminder").requires_approval("direct")
    assert reg.get("create_reminder").requires_approval("approval")
    assert not reg.get("get_bills").requires_approval("approval")


# --- tasks ---


async def test_get_tasks_open_filters_and_search(tool_ctx):
    h, ctx = tool_ctx
    out = await run(h, ctx, "get_tasks", {"status": "open", "priority": "high"})
    assert [t["title"] for t in out["items"]] == ["ML assignment 3"]
    out = await run(h, ctx, "get_tasks", {"query": "DBMS"})
    assert [t["title"] for t in out["items"]] == ["DBMS assignment"]


async def test_create_task_sends_camel_case(tool_ctx):
    h, ctx = tool_ctx
    due = (ctx.today + timedelta(days=1)).isoformat()
    out = await run(h, ctx, "create_task", {"title": "Finish ML assignment", "category": "academic", "due_date": due, "due_time": "17:30"})
    stored = h.fake.data[USER_A]["tasks"][-1]
    assert stored["dueDate"] == due and stored["dueTime"] == "17:30" and stored["category"] == "academic"
    assert out["title"] == "Finish ML assignment"


async def test_get_update_complete_delete_task(tool_ctx):
    h, ctx = tool_ctx
    task_id = ids(h, "tasks")[0]
    assert (await run(h, ctx, "get_task", {"task_id": task_id}))["id"] == task_id
    assert (await run(h, ctx, "update_task", {"task_id": task_id, "priority": "low"}))["priority"] == "low"
    assert (await run(h, ctx, "complete_task", {"task_id": task_id}))["status"] == "completed"
    out = await run(h, ctx, "delete_task", {"task_id": task_id})
    assert out["deleted"] and task_id not in ids(h, "tasks")


async def test_invalid_task_input_is_rejected_before_any_call(tool_ctx):
    h, ctx = tool_ctx
    before = len(h.fake.calls)
    with pytest.raises(ToolInputError, match="title"):
        h.services.registry.get("create_task").parse({"title": "", "category": "not-a-category"})
    with pytest.raises(ToolInputError, match="Extra inputs"):
        h.services.registry.get("get_tasks").parse({"drop_table": True})
    assert len(h.fake.calls) == before


async def test_missing_task_is_a_safe_error(tool_ctx):
    h, ctx = tool_ctx
    with pytest.raises(ToolError, match="not found"):
        await run(h, ctx, "get_task", {"task_id": "does-not-exist"})


# --- events ---


async def test_event_tools(tool_ctx):
    h, ctx = tool_ctx
    out = await run(h, ctx, "get_events", {})
    assert [e["title"] for e in out["items"]] == ["ML lecture"]
    tomorrow = (ctx.today + timedelta(days=1)).isoformat()
    created = await run(h, ctx, "create_event", {"title": "Project meeting", "event_type": "project_meeting",
                                                 "date": tomorrow, "start_time": "17:00"})
    assert h.fake.data[USER_A]["events"][-1]["endTime"] == "18:00"  # defaulted to one hour
    updated = await run(h, ctx, "update_event", {"event_id": created["id"], "location": "Library"})
    assert updated["location"] == "Library"
    assert (await run(h, ctx, "delete_event", {"event_id": created["id"]}))["deleted"]


async def test_event_range_is_bounded(harness):
    tool = harness.services.registry.get("get_events")
    with pytest.raises(ToolInputError, match="62"):
        tool.parse({"start_date": "2026-01-01", "end_date": "2026-06-01"})


# --- reminders ---


async def test_reminder_tools(tool_ctx):
    h, ctx = tool_ctx
    assert len((await run(h, ctx, "get_reminders", {}))["items"]) == 1
    created = await run(h, ctx, "create_reminder", {"title": "Pay electricity bill",
                                                    "date": (ctx.today + timedelta(days=1)).isoformat(), "time": "19:00"})
    assert h.fake.data[USER_A]["reminders"][-1]["time"] == "19:00"
    no_time = await run(h, ctx, "create_reminder", {"title": "Review plan", "date": ctx.today.isoformat(), "repeat_rule": "weekly"})
    assert no_time["time"] == "09:00"  # the user's preferred reminder time
    assert (await run(h, ctx, "snooze_reminder", {"reminder_id": created["id"], "minutes": 15}))["status"] == "snoozed"
    assert (await run(h, ctx, "complete_reminder", {"reminder_id": created["id"]}))["status"] == "completed"
    assert (await run(h, ctx, "cancel_reminder", {"reminder_id": no_time["id"]}))["status"] == "cancelled"


# --- study ---


async def test_study_tools(tool_ctx):
    h, ctx = tool_ctx
    subjects = await run(h, ctx, "get_subjects", {})
    assert {s["name"] for s in subjects["items"]} == {"Machine Learning", "Database Management Systems"}
    plan = await run(h, ctx, "create_study_plan", {"subject": "Machine Learning", "days": 3, "title": "ML exam prep"})
    assert plan["title"] == "ML exam prep" and len(plan["sessions"]) == 3
    assert ("POST", "/api/v1/study-plans/generate") in h.fake.calls and ("POST", "/api/v1/study-plans") in h.fake.calls
    listed = await run(h, ctx, "get_study_plan", {})
    assert listed["total"] == 1
    one = await run(h, ctx, "get_study_plan", {"plan_id": plan["id"]})
    assert one["items"][0]["id"] == plan["id"]
    assert (await run(h, ctx, "update_study_plan", {"plan_id": plan["id"], "status": "completed"}))["status"] == "completed"
    session = await run(h, ctx, "create_study_session", {"topic": "Backprop", "date": ctx.today.isoformat(),
                                                         "start_time": "18:00", "end_time": "19:00"})
    assert (await run(h, ctx, "complete_study_session", {"session_id": session["id"]}))["status"] == "completed"
    sessions = await run(h, ctx, "get_study_sessions", {})
    assert sessions["total"] >= 4


async def test_study_session_times_are_validated(harness):
    with pytest.raises(ToolInputError, match="end_time"):
        harness.services.registry.get("create_study_session").parse(
            {"topic": "x", "date": "2026-01-01", "start_time": "19:00", "end_time": "18:00"})


# --- finance ---


async def test_bill_tools(tool_ctx):
    h, ctx = tool_ctx
    due_week = await run(h, ctx, "get_bills", {"due_within_days": 7})
    assert [b["title"] for b in due_week["items"]] == ["Electricity bill"]
    created = await run(h, ctx, "create_bill", {"title": "Electricity bill", "amount": 1200, "category": "electricity",
                                                "due_date": (ctx.today + timedelta(days=1)).isoformat()})
    assert created["amount"] == 1200
    assert (await run(h, ctx, "update_bill", {"bill_id": created["id"], "amount": 1300}))["amount"] == 1300
    paid = await run(h, ctx, "mark_bill_paid", {"bill_id": created["id"], "payment_method": "UPI"})
    assert paid["bill"]["status"] == "paid" and paid["payment"]["amount"] == 1300
    assert (await run(h, ctx, "get_payments", {}))["total"] == 1


async def test_payment_plan_expense_and_subscription_tools(tool_ctx):
    h, ctx = tool_ctx
    plan = await run(h, ctx, "create_payment_plan", {"title": "Semester fees", "total_amount": 60000,
                                                     "installment_amount": 10000, "start_date": ctx.today.isoformat()})
    assert plan["total_installments"] == 6
    assert (await run(h, ctx, "get_payment_plans", {}))["total"] == 1
    summary = await run(h, ctx, "get_expense_summary", {})
    assert summary["total"] == 1150 and summary["count"] == 2
    expense = await run(h, ctx, "create_expense", {"title": "Books", "amount": 450, "category": "education"})
    assert expense["expense_date"] == ctx.today.isoformat()  # defaulted to today
    assert (await run(h, ctx, "get_expenses", {}))["total"] == 3
    subs = await run(h, ctx, "get_subscriptions", {"renewing_within_days": 7})
    assert [s["name"] for s in subs["items"]] == ["Spotify"]
    assert (await run(h, ctx, "get_subscriptions", {"renewing_within_days": 1}))["items"] == []
    created = await run(h, ctx, "create_subscription", {"name": "Notion", "amount": 400})
    assert created["name"] == "Notion"


async def test_finance_tools_never_move_money(harness):
    """Finance tools only call tracking endpoints; there is no payment-execution surface."""
    finance = [t for t in harness.services.registry.tools() if t.domain.value == "finance"]
    text = " ".join(f"{t.name} {t.description} {t.input_model.model_json_schema()}" for t in finance).lower()
    for forbidden in ("card_number", "cvv", "account_number", "iban", "transfer", "upi_pin"):
        assert forbidden not in text
    with pytest.raises(ToolInputError):
        harness.services.registry.get("create_expense").parse({"title": "x", "amount": -5})


# --- goals ---


async def test_goal_tools(tool_ctx):
    h, ctx = tool_ctx
    active = await run(h, ctx, "get_goals", {})
    assert len(active["items"]) == 2
    goal = await run(h, ctx, "create_goal", {"title": "Save ₹20,000", "category": "financial", "target_value": 20000, "unit": "INR"})
    assert goal["target_value"] == 20000
    internship = next(g for g in h.fake.data[USER_A]["goals"] if "internship" in g["title"])
    out = await run(h, ctx, "update_goal_progress", {"goal_id": internship["id"], "progress": 60})
    assert out["progress"] == 60
    assert (await run(h, ctx, "update_goal", {"goal_id": goal["id"], "status": "on_hold"}))["status"] == "on_hold"
    with pytest.raises(ToolInputError):
        await run(h, ctx, "update_goal_progress", {"goal_id": goal["id"]})


# --- documents ---


async def test_document_tools(tool_ctx):
    h, ctx = tool_ctx
    doc = h.fake.add_document(USER_A, "DBMS notes.txt", "Normalization removes redundancy.\n\nJoins combine tables.")
    listed = await run(h, ctx, "get_documents", {})
    assert [d["name"] for d in listed["items"]] == ["DBMS notes.txt"]
    assert (await run(h, ctx, "get_document", {"document_id": doc["id"]}))["name"] == "DBMS notes.txt"
    found = await run(h, ctx, "search_documents", {"query": "what is normalization"})
    assert found["chunks"] and found["chunks"][0]["document_name"] == "DBMS notes.txt"
    assert "Normalization" in found["chunks"][0]["text"]


async def test_search_documents_calls_the_backend_search_api(tool_ctx):
    h, ctx = tool_ctx
    doc = h.fake.add_document(USER_A, "ML notes.txt", "Overfitting happens with high variance.")
    seen = []
    original = h.fake._search_documents

    def spy(d, body):
        seen.append(body)
        return original(d, body)

    h.fake._search_documents = spy
    await run(h, ctx, "search_documents", {"query": "overfitting", "document_ids": [doc["id"]], "limit": 3})
    assert seen == [{"query": "overfitting", "topK": 3, "documentIds": [doc["id"]]}]
    assert ("POST", "/api/v1/documents/search") in h.fake.calls or any(p.endswith("/documents/search") for _, p in h.fake.calls)


async def test_search_documents_empty_result(tool_ctx):
    h, ctx = tool_ctx
    h.fake.add_document(USER_A, "ML notes.txt", "Overfitting happens with high variance.")
    found = await run(h, ctx, "search_documents", {"query": "quantum computing"})
    assert found["chunks"] == [] and found["message"] == "No relevant document content found."


async def test_search_documents_only_sees_the_callers_documents(tool_ctx):
    h, ctx = tool_ctx
    h.fake.add_document(USER_B, "B private.txt", "Overfitting happens with high variance.")
    found = await run(h, ctx, "search_documents", {"query": "overfitting variance"})
    assert found["chunks"] == []  # user A's token: the backend scopes the search to user A


async def test_search_documents_backend_failure_is_a_tool_error(tool_ctx):
    h, ctx = tool_ctx
    h.fake.fail[r"/documents/search"] = 503
    with pytest.raises(ToolError):
        await run(h, ctx, "search_documents", {"query": "overfitting"})


# --- memory ---


async def test_remember_preference_is_validated_and_persisted_via_backend(tool_ctx):
    h, ctx = tool_ctx
    out = await run(h, ctx, "remember_preference", {"key": "preferred_study_start", "value": "19:30"})
    assert out["value"] == "19:30"
    assert h.fake.prefs[USER_A]["preferredStudyStart"] == "19:30"
    with pytest.raises(ToolInputError):
        await run(h, ctx, "remember_preference", {"key": "preferred_study_start", "value": "evening"})
    with pytest.raises(ToolInputError):
        await run(h, ctx, "remember_preference", {"key": "favourite_food", "value": "pizza"})


# --- permissions & failures ---


async def test_scopes_limit_what_a_tool_may_do(tool_ctx):
    h, ctx = tool_ctx
    ctx.scopes = frozenset({"tasks:read"})
    assert (await run(h, ctx, "get_tasks", {}))["items"]
    with pytest.raises(ToolPermissionError):
        await run(h, ctx, "create_task", {"title": "x"})


async def test_backend_outage_becomes_tool_error(tool_ctx):
    h, ctx = tool_ctx
    h.fake.fail[r"/bills"] = 503
    with pytest.raises(ToolError, match="AgentOS service"):
        await run(h, ctx, "get_bills", {})


async def test_backend_validation_error_is_reported(tool_ctx):
    h, ctx = tool_ctx
    tool = h.services.registry.get("create_task")
    args = tool.parse({"title": "ok"})
    args.title = ""  # bypass local validation to exercise the backend's 422 path
    with pytest.raises(ToolError, match="rejected"):
        await h.services.registry.execute(tool, args, ctx)


async def test_langchain_export_is_read_only(tool_ctx):
    h, ctx = tool_ctx
    tools = h.services.registry.as_langchain_tools(ctx)
    names = {t.name for t in tools}
    assert "get_tasks" in names and "create_task" not in names and "delete_task" not in names
    get_bills = next(t for t in tools if t.name == "get_bills")
    out = await get_bills.ainvoke({"due_within_days": 7})
    assert out["items"][0]["title"] == "Electricity bill"


# --- budgets, subjects, subscription updates ---


async def test_budget_tools_create_then_update(tool_ctx):
    h, ctx = tool_ctx
    created = await run(h, ctx, "set_budget", {"amount": 5000, "category": "food"})
    assert created["amount"] == 5000 and created["category"] == "food"
    updated = await run(h, ctx, "set_budget", {"amount": 6000, "category": "food", "alert_threshold": 90})
    assert updated["id"] == created["id"] and updated["amount"] == 6000  # same budget, not a duplicate
    listed = await run(h, ctx, "get_budgets", {})
    food = next(b for b in listed["items"] if b["category"] == "food")
    assert food["spent"] == 850 and food["status"] == "on_track"
    overall = await run(h, ctx, "set_budget", {"amount": 10000})
    assert overall.get("category") is None and len(h.fake.data[USER_A]["budgets"]) == 2


async def test_create_subject_and_update_subscription(tool_ctx):
    h, ctx = tool_ctx
    subj = await run(h, ctx, "create_subject", {"name": "Operating Systems", "code": "OS"})
    assert subj["name"] == "Operating Systems" and h.fake.data[USER_A]["subjects"][-1]["code"] == "OS"
    spotify = next(x for x in h.fake.data[USER_A]["subscriptions"] if x["name"] == "Spotify")
    out = await run(h, ctx, "update_subscription", {"subscription_id": spotify["id"], "status": "paused"})
    assert out["status"] == "paused"


def test_every_frontend_section_has_agent_tools(harness):
    names = set(harness.services.registry.names)
    sections = {
        "Tasks": {"get_tasks", "create_task", "update_task", "complete_task", "delete_task"},
        "Calendar": {"get_events", "create_event", "update_event", "delete_event"},
        "Reminders": {"get_reminders", "create_reminder", "complete_reminder", "snooze_reminder", "cancel_reminder"},
        "Goals": {"get_goals", "create_goal", "update_goal", "update_goal_progress"},
        "Study plan": {"get_subjects", "create_subject", "get_study_plan", "create_study_plan", "create_study_session",
                       "complete_study_session"},
        "Documents": {"get_documents", "get_document", "search_documents"},
        "Bills & payments": {"get_bills", "create_bill", "update_bill", "mark_bill_paid", "get_payments",
                             "get_payment_plans", "create_payment_plan", "get_subscriptions", "create_subscription",
                             "update_subscription"},
        "Expenses": {"get_expenses", "get_expense_summary", "create_expense"},
        "Budgets": {"get_budgets", "set_budget"},
        "Preferences (memory)": {"remember_preference"},
    }
    missing = {section: tools - names for section, tools in sections.items() if tools - names}
    assert not missing
