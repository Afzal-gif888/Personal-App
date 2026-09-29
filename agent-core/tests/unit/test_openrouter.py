"""OpenRouter provider against a stubbed chat-completions API (no key or network needed)."""

import json

import httpx
import pytest

from app.llm.base import LLMError, LLMToolSpec
from app.llm.factory import create_llm_provider
from app.llm.openrouter import OpenRouterProvider, from_chat_response, to_chat_messages, to_openai_schema
from app.schemas.agent import RunStatus
from tests.conftest import Harness, make_settings
from tests.fakes import USER_A

KEY = "sk-or-v1-test-key"
TOOLS = [LLMToolSpec("get_bills", "List bills", {"type": "object", "properties": {"due_within_days": {"type": "integer"}}})]
USER = [{"role": "user", "content": "What bills are due?"}]


def settings(**kw):
    return make_settings(llm_provider="openrouter", llm_api_key=KEY, **kw)


def reply(text=None, calls=(), finish="stop", model="qwen/qwen3.8-27b:free"):
    message = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = [{"id": cid, "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
                                 for cid, n, a in calls]
        finish = "tool_calls"
    return {"id": "gen-1", "model": model, "choices": [{"message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


class Stub:
    def __init__(self, *responses):
        self.queue = list(responses)
        self.bodies, self.headers = [], []

    def provider(self, **kw):
        def handle(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v1/chat/completions"
            self.bodies.append(json.loads(request.content))
            self.headers.append(request.headers)
            item = self.queue.pop(0)
            if isinstance(item, tuple):
                return httpx.Response(item[0], json=item[1], headers=item[2] if len(item) > 2 else {})
            return httpx.Response(200, json=item)

        return OpenRouterProvider(settings(**kw), transport=httpx.MockTransport(handle))


def test_factory_and_no_key():
    assert create_llm_provider(settings()).name == "openrouter"
    assert create_llm_provider(make_settings(llm_provider="openrouter")).name == "unconfigured"


def test_transcript_translation():
    messages = [
        {"role": "user", "content": "What bills are due?"},
        {"role": "assistant", "content": [{"type": "text", "text": "Checking."},
                                          {"type": "tool_use", "id": "c1", "name": "get_bills", "input": {"due_within_days": 7}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1", "content": '{"items": []}'}]},
    ]
    assert to_chat_messages("sys", messages) == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "What bills are due?"},
        {"role": "assistant", "content": "Checking.", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "get_bills", "arguments": '{"due_within_days": 7}'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": '{"items": []}'},
    ]


def test_response_parsing():
    blocks, stop = from_chat_response(reply(calls=[("c9", "get_bills", {"due_within_days": 7})]))
    assert stop == "tool_use" and blocks == [{"type": "tool_use", "id": "c9", "name": "get_bills", "input": {"due_within_days": 7}}]
    assert from_chat_response(reply("All paid."))[0] == [{"type": "text", "text": "All paid."}]
    assert from_chat_response(reply("cut", finish="length"))[1] == "max_tokens"
    bad = {"choices": [{"message": {"tool_calls": [{"id": "c", "function": {"name": "get_bills", "arguments": "{oops"}}]}}]}
    assert "_malformed_arguments" in from_chat_response(bad)[0][0]["input"]


def test_schema_is_self_contained():
    schema = {"type": "object", "title": "X", "properties": {
        "key": {"$ref": "#/$defs/K"}, "n": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": None, "description": "N"}},
        "$defs": {"K": {"title": "K", "type": "string", "enum": ["a"]}}}
    assert to_openai_schema(schema) == {"type": "object", "properties": {
        "key": {"type": "string", "enum": ["a"]}, "n": {"type": "integer", "description": "N"}}}


async def test_request_shape_uses_in_request_fallbacks():
    stub = Stub(reply(calls=[("c1", "get_bills", {})]))
    result = await stub.provider().invoke(system="sys", messages=USER, tools=TOOLS)
    body, headers = stub.bodies[0], stub.headers[0]
    assert headers["authorization"] == f"Bearer {KEY}" and headers["x-title"] == "It's Personal"
    assert body["model"] == "qwen/qwen3.8-27b:free"
    assert body["models"][0] == body["model"] and len(body["models"]) == 3  # OpenRouter falls back inside one request
    assert body["tools"][0]["function"]["name"] == "get_bills" and body["tool_choice"] == "auto"
    assert body["max_tokens"] == 4096
    assert result.tool_calls[0].name == "get_bills" and len(stub.bodies) == 1


async def test_rate_limit_is_not_retried_unless_the_wait_is_short(monkeypatch):
    async def no_sleep(_):
        return None

    monkeypatch.setattr("app.llm.openrouter.asyncio.sleep", no_sleep)
    long_wait = Stub((429, {"error": {"code": 429, "message": "rate limited"}}, {"retry-after": "60"}))
    with pytest.raises(LLMError) as info:
        await long_wait.provider().invoke(system="", messages=USER, tools=[])
    assert info.value.rate_limited and len(long_wait.bodies) == 1  # no extra request burned
    short_wait = Stub((429, {"error": {"code": 429}}, {"retry-after": "1"}), reply("ok"))
    assert (await short_wait.provider().invoke(system="", messages=USER, tools=[])).text == "ok"
    assert len(short_wait.bodies) == 2


@pytest.mark.parametrize("status,message", [(401, "rejected"), (402, "no credits"), (404, "LLM_MODEL"), (400, "couldn't process")])
async def test_errors_are_safe(status, message):
    stub = Stub((status, {"error": {"code": status, "message": "upstream detail secret"}}))
    with pytest.raises(LLMError) as info:
        await stub.provider().invoke(system="", messages=USER, tools=[])
    assert message in info.value.message and "secret" not in info.value.message


async def test_error_inside_a_200_body():
    stub = Stub({"error": {"code": 503, "message": "provider down"}}, {"error": {"code": 503}})
    with pytest.raises(LLMError, match="busy"):
        await stub.provider().invoke(system="", messages=USER, tools=[])


async def test_full_agent_run_with_openrouter(backend):
    stub = Stub(reply(calls=[("c1", "get_bills", {"due_within_days": 7})]), reply("Your electricity bill of ₹1,200 is due in 3 days."))
    r = await Harness(backend, settings(), llm=stub.provider()).run("What bills are due this week?")
    assert r.status == RunStatus.COMPLETED and [t.name for t in r.tool_calls] == ["get_bills"]
    assert r.response.startswith("Your electricity bill") and len(stub.bodies) == 2  # one call to act, one to answer
    tool_msg = stub.bodies[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and "Electricity bill" in tool_msg["content"]
    assert backend.data[USER_A]["bills"]


async def test_request_budget_stops_calls_before_they_are_spent():
    from app.llm.budget import BudgetedProvider, RequestBudget

    stub = Stub(reply("one"), reply("two"), reply("three"))
    llm = BudgetedProvider(stub.provider(), RequestBudget(per_minute=2, per_day=10))
    assert (await llm.invoke(system="", messages=USER, tools=[])).text == "one"
    assert (await llm.invoke(system="", messages=USER, tools=[])).text == "two"
    with pytest.raises(LLMError, match="try again in a minute") as info:
        await llm.invoke(system="", messages=USER, tools=[])
    assert info.value.rate_limited and len(stub.bodies) == 2  # the third request never left the app


async def test_daily_budget_and_factory_wrapping():
    from app.llm.budget import RequestBudget

    budget = RequestBudget(per_day=1)
    budget.take()
    with pytest.raises(LLMError, match="today's request allowance"):
        budget.take()
    wrapped = create_llm_provider(settings(llm_max_requests_per_minute=15, llm_max_requests_per_day=45))
    assert wrapped.name == "openrouter" and type(wrapped).__name__ == "BudgetedProvider"
    assert type(create_llm_provider(settings())).__name__ == "OpenRouterProvider"  # no caps configured
