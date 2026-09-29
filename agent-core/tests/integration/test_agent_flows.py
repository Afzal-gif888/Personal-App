"""End-to-end runs of the LangGraph workflow: mock LLM + real tools + fake backend."""

import asyncio

from app.llm.base import LLMError, LLMProvider, LLMResult
from app.schemas.agent import ErrorCode, RunStatus
from app.schemas.memory import ConversationTurn
from tests.conftest import Harness, make_settings
from tests.fakes import TOKEN_B, USER_A, USER_B
from tests.mock_llm import MockLLMProvider


def types(result):
    return [e["type"] for e in result.events]


def err(result):
    assert result.error is not None
    return result.error


def tool_names(result):
    return [t.name for t in result.tool_calls]


def tool_use(*calls, text="Checking."):
    blocks = [{"type": "text", "text": text}]
    blocks += [{"type": "tool_use", "id": f"toolu_{i}_{name}", "name": name, "input": args} for i, (name, args) in enumerate(calls)]
    return LLMResult(content=blocks, stop_reason="tool_use")


def answer(text):
    return LLMResult(content=[{"type": "text", "text": text}])


# --- simple, multi-step and the example behaviours ---


async def test_simple_request_selects_one_read_tool(harness):
    r = await harness.run("What bills are due this week?")
    assert r.status == RunStatus.COMPLETED and tool_names(r) == ["get_bills"]
    assert "Electricity bill" in r.response and "Hostel rent" not in r.response
    assert types(r)[:3] == ["RUN_STARTED", "CONTEXT_LOADED", "REQUEST_UNDERSTOOD"]
    assert {"PLANNING_STARTED", "PLAN_CREATED", "TOOL_STARTED", "TOOL_COMPLETED", "RUN_COMPLETED"} <= set(types(r))
    assert r.metadata["iterations"] == 2 and not r.approval_required


async def test_weekly_overview_combines_every_area(harness):
    r = await harness.run("What do I need to take care of this week?")
    assert r.status == RunStatus.COMPLETED
    assert set(tool_names(r)) == {"get_tasks", "get_events", "get_bills", "get_reminders", "get_goals"}
    for item in ("ML assignment 3", "ML lecture", "Electricity bill", "Review study plan", "internship"):
        assert item in r.response
    assert r.metadata["plan_steps"] > 1  # multi-step requests get an explicit planning pass


async def test_study_plan_gathers_context_before_acting(harness):
    r = await harness.run("I have an ML exam next Friday. Make me a study plan.")
    names = tool_names(r)
    assert names[-1] == "create_study_plan" and {"get_subjects", "get_tasks", "get_events"} <= set(names[:-1])
    plan_call = r.tool_calls[-1]
    assert plan_call.input["subject"] == "Machine Learning" and plan_call.status.value == "completed"
    assert harness.fake.data[USER_A]["study_plans"]


async def test_reminder_is_created_and_confirmed(harness):
    r = await harness.run("Remind me to pay my electricity bill tomorrow at 7 PM.")
    assert r.status == RunStatus.COMPLETED and tool_names(r) == ["create_reminder"]
    stored = harness.fake.data[USER_A]["reminders"][-1]
    assert stored["title"] == "Pay my electricity bill" and stored["time"] == "19:00"
    assert "Pay my electricity bill" in r.response


async def test_document_question_uses_rag(harness):
    harness.fake.add_document(USER_A, "DBMS notes.txt",
                              "Normalization organises tables to reduce redundancy.\n\nIndexes speed up lookups.")
    r = await harness.run("According to my uploaded notes, explain normalization.")
    assert "DOCUMENTS_RETRIEVED" in types(r)
    assert r.retrieved_documents and r.retrieved_documents[0]["document_name"] == "DBMS notes.txt"
    assert "Normalization organises tables" in r.response


async def test_unrelated_request_does_not_touch_documents(harness):
    harness.fake.add_document(USER_A, "DBMS notes.txt", "Normalization organises tables.")
    r = await harness.run("What bills are due this week?")
    assert "DOCUMENTS_RETRIEVED" not in types(r) and r.retrieved_documents == []
    assert not any("/documents" in path for _, path in harness.fake.calls)


async def test_only_scoped_tools_are_offered(harness):
    await harness.run("What bills are due this week?")
    offered = harness.services.llm.calls[-1]["tools"]
    assert "get_bills" in offered and "search_documents" not in offered and "create_goal" not in offered


# --- approvals ---


async def test_delete_requires_approval_and_nothing_is_deleted(harness):
    r = await harness.run("Delete my DBMS assignment task")
    assert r.status == RunStatus.APPROVAL_REQUIRED and r.approval_required
    [approval] = r.approvals
    assert approval.action_type == "delete_task" and approval.reason
    dbms = next(t for t in harness.fake.data[USER_A]["tasks"] if t["title"] == "DBMS assignment")
    assert approval.action_payload == {"task_id": dbms["id"]}
    assert "APPROVAL_REQUIRED" in types(r) and "approval" in r.response.lower()


async def test_mutation_policy_can_require_approval_for_creates(backend):
    h = Harness(backend, make_settings(mutation_policy="approval"))
    r = await h.run("Remind me to pay my electricity bill tomorrow at 7 PM.")
    assert r.status == RunStatus.APPROVAL_REQUIRED and r.approvals[0].action_type == "create_reminder"
    assert len(backend.data[USER_A]["reminders"]) == 1  # only the seeded one


# --- failures and limits ---


async def test_tool_failure_is_reported_not_raised(harness):
    harness.fake.fail[r"/bills"] = 503
    r = await harness.run("What bills are due this week?")
    assert r.status == RunStatus.COMPLETED
    assert r.tool_calls[0].status.value == "failed" and "TOOL_FAILED" in types(r)
    assert "couldn't" in r.response.lower() and "Traceback" not in r.response


async def test_malformed_and_unknown_tool_calls_are_fed_back(backend):
    llm = MockLLMProvider([
        tool_use(("create_task", {"title": ""}), ("launch_rockets", {})),
        answer("Sorry, I couldn't create that task."),
    ])
    r = await Harness(backend, make_settings(), llm).run("Hello")
    assert [t.status.value for t in r.tool_calls] == ["failed", "failed"]
    assert "Invalid input" in (r.tool_calls[0].error or "") and "Unknown tool" in (r.tool_calls[1].error or "")
    assert r.status == RunStatus.COMPLETED and r.response == "Sorry, I couldn't create that task."


async def test_iteration_limit_stops_the_loop(backend):
    llm = MockLLMProvider([tool_use(("get_tasks", {})) for _ in range(10)])
    r = await Harness(backend, make_settings(max_agent_iterations=3), llm).run("Hello")
    assert r.status == RunStatus.INCOMPLETE and err(r).code == ErrorCode.ITERATION_LIMIT
    assert r.metadata["iterations"] == 3 and "LIMIT_REACHED" in types(r)
    assert "What I got done" in r.response


async def test_tool_call_limit_stops_before_running_extra_tools(backend):
    llm = MockLLMProvider([tool_use(("get_tasks", {}), ("get_bills", {})), tool_use(("get_goals", {}), ("get_events", {}))])
    r = await Harness(backend, make_settings(max_tool_calls=3), llm).run("Hello")
    assert r.status == RunStatus.INCOMPLETE and err(r).code == ErrorCode.TOOL_LIMIT
    assert tool_names(r) == ["get_tasks", "get_bills"]


class SlowLLM(LLMProvider):
    name = "slow"

    async def invoke(self, **kwargs):
        await asyncio.sleep(5)
        return answer("too late")


async def test_timeout_fails_gracefully(backend):
    r = await Harness(backend, make_settings(agent_timeout_seconds=0.3), SlowLLM()).run("Hello")
    assert r.status == RunStatus.FAILED and err(r).code == ErrorCode.TIMEOUT and err(r).retryable
    assert "RUN_STARTED" in types(r) and types(r)[-1] == "RUN_FAILED"


class BrokenLLM(LLMProvider):
    name = "broken"

    def __init__(self, error):
        self.error = error

    async def invoke(self, **kwargs):
        raise self.error


async def test_llm_failure_and_rate_limit(backend):
    r = await Harness(backend, make_settings(), BrokenLLM(LLMError("The assistant is temporarily unavailable.", retryable=True))).run("Hello")
    assert r.status == RunStatus.FAILED and err(r).code == ErrorCode.LLM_ERROR and r.response.startswith("The assistant")
    r = await Harness(backend, make_settings(), BrokenLLM(LLMError("busy", retryable=True, rate_limited=True))).run("Hello")
    assert err(r).code == ErrorCode.RATE_LIMITED


async def test_unexpected_crash_never_leaks_internals(backend):
    r = await Harness(backend, make_settings(), BrokenLLM(RuntimeError("db password=hunter2 at line 42"))).run("Hello")
    assert r.status == RunStatus.FAILED and err(r).code == ErrorCode.INTERNAL_ERROR
    assert "hunter2" not in r.model_dump_json() and "line 42" not in r.response


async def test_refusal_is_handled(backend):
    llm = MockLLMProvider([LLMResult(content=[], stop_reason="refusal")])
    r = await Harness(backend, make_settings(), llm).run("Hello")
    assert r.status == RunStatus.COMPLETED and "can't help" in r.response


async def test_backend_unavailable_during_context_load(harness):
    harness.fake.fail[r"/users/me$"] = 503
    r = await harness.run("What are my tasks?")
    assert r.status == RunStatus.FAILED and err(r).code == ErrorCode.BACKEND_UNAVAILABLE and err(r).retryable


async def test_oversized_request_is_rejected(backend):
    r = await Harness(backend, make_settings(max_request_chars=100)).run("x" * 101)
    assert r.status == RunStatus.FAILED and err(r).code == ErrorCode.INVALID_REQUEST


# --- identity and context ---


async def test_user_id_must_match_the_token(harness):
    r = await harness.run("What are my tasks?", user_id=USER_B)
    assert err(r).code == ErrorCode.FORBIDDEN and r.tool_calls == []
    ok = await harness.run("What are my tasks?", user_id=USER_A)
    assert ok.status == RunStatus.COMPLETED


async def test_each_user_only_sees_their_own_data(harness):
    r = await harness.run("What are my tasks?", token=TOKEN_B)
    assert r.status == RunStatus.COMPLETED and "ML assignment" not in r.response


async def test_history_is_used_as_short_term_memory(harness):
    history = [ConversationTurn(role="user", content="Hi"), ConversationTurn(role="assistant", content="Hello Asha!")]
    await harness.run("What are my tasks?", history=history)
    assert harness.services.llm.calls[-1]["messages"] >= 3  # history + request (+ tool turns)


async def test_context_is_bounded_and_relevant(backend):
    llm = MockLLMProvider([answer("ok")])
    h = Harness(backend, make_settings(), llm)

    captured = {}
    original = llm.invoke

    async def spy(**kwargs):
        captured["system"] = kwargs["system"]
        return await original(**kwargs)

    llm.invoke = spy  # type: ignore[method-assign]
    await h.run("What bills are due this week?")
    system = captured["system"]
    assert "Electricity bill" in system and "Today is" in system and "Asia/Kolkata" in system
    assert "ML lecture" not in system and "Spotify" not in system  # other domains are not loaded
