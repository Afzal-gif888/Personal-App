"""LLM layer: the mock is deterministic; the Anthropic provider is exercised against a stub client."""

from types import SimpleNamespace
from typing import cast

import anthropic
import httpx2 as httpx  # anthropic 1.x uses httpx2 for its request/response types
import pytest

from app.llm.base import LLMError, LLMResult, LLMToolSpec
from app.llm.factory import create_llm_provider
from app.llm.provider import FALLBACK_BETA, AnthropicProvider, sanitize_fallback_content
from tests.conftest import make_settings
from tests.mock_llm import MockLLMProvider

TOOLS = [LLMToolSpec("get_bills", "List bills", {"type": "object", "properties": {}}),
         LLMToolSpec("create_reminder", "Create reminder", {"type": "object", "properties": {}})]
SYSTEM = "Today is 2026-09-28."


async def test_mock_is_deterministic_and_selects_tools():
    msgs = [{"role": "user", "content": "What bills are due this week?"}]
    a = await MockLLMProvider().invoke(system=SYSTEM, messages=msgs, tools=TOOLS)
    b = await MockLLMProvider().invoke(system=SYSTEM, messages=msgs, tools=TOOLS)
    assert [c.model_dump() for c in a.tool_calls] == [c.model_dump() for c in b.tool_calls]
    assert a.tool_calls[0].name == "get_bills" and a.tool_calls[0].input == {"due_within_days": 7}


async def test_mock_parses_reminder_time_and_date():
    msgs = [{"role": "user", "content": "Remind me to pay electricity bill tomorrow at 7 PM."}]
    call = (await MockLLMProvider().invoke(system=SYSTEM, messages=msgs, tools=TOOLS)).tool_calls[0]
    assert call.input == {"title": "Pay electricity bill", "date": "2026-09-29", "time": "19:00", "repeat_rule": "none"}


async def test_mock_only_calls_offered_tools_and_answers_after_results():
    msgs = [{"role": "user", "content": "What bills are due this week?"}]
    none = await MockLLMProvider().invoke(system=SYSTEM, messages=msgs, tools=[])
    assert not none.tool_calls and none.text
    first = await MockLLMProvider().invoke(system=SYSTEM, messages=msgs, tools=TOOLS)
    msgs += [{"role": "assistant", "content": first.content},
             {"role": "user", "content": [{"type": "tool_result", "tool_use_id": first.tool_calls[0].id,
                                           "content": '{"items": [{"title": "Electricity bill"}], "total": 1}'}]}]
    final = await MockLLMProvider().invoke(system=SYSTEM, messages=msgs, tools=TOOLS)
    assert not final.tool_calls and "Electricity bill" in final.text


async def test_scripted_mock_and_exhaustion():
    llm = MockLLMProvider([LLMResult(content=[{"type": "text", "text": "hi"}])])
    assert (await llm.invoke(system="", messages=[], tools=[])).text == "hi"
    with pytest.raises(LLMError):
        await llm.invoke(system="", messages=[], tools=[])


async def test_no_key_means_unconfigured_never_a_fake_assistant():
    provider = create_llm_provider(make_settings(llm_provider="anthropic"))
    assert provider.name == "unconfigured"
    with pytest.raises(LLMError, match="isn't set up yet"):
        await provider.invoke(system="", messages=[{"role": "user", "content": "hi"}], tools=[])
    assert create_llm_provider(make_settings(llm_provider="anthropic", llm_api_key="sk-test-key")).name == "anthropic"
    with pytest.raises(ValueError):
        make_settings(llm_provider="mock")  # the mock is not a selectable provider


async def test_unconfigured_agent_reports_it_and_is_not_ready(backend):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(make_settings(), backend_transport=backend.transport())
    with TestClient(app) as client:
        ready = client.get("/ready")
        assert ready.status_code == 503 and ready.json()["checks"]["llm"] == "unconfigured"
    from tests.conftest import Harness

    r = await Harness(backend, make_settings(), llm=create_llm_provider(make_settings())).run("What bills are due?")
    assert r.status.value == "failed" and "isn't set up yet" in r.response


def test_production_requires_key_and_service_token():
    with pytest.raises(ValueError, match="AGENT_CORE_SERVICE_TOKEN"):
        make_settings(app_env="production")
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        create_llm_provider(make_settings(app_env="production", agent_core_service_token="x", llm_provider="anthropic"))


def test_api_key_is_never_rendered():
    s = make_settings(llm_api_key="sk-ant-supersecret-value")
    assert "supersecret" not in repr(s) and "supersecret" not in str(s.model_dump())


class Block(dict):
    def to_dict(self):
        return dict(self)


def stub_provider(model="claude-opus-5", *, fail: Exception | None = None, blocks=None):
    provider = AnthropicProvider(make_settings(llm_provider="anthropic", llm_api_key="sk-test", llm_model=model))
    calls: dict = {}

    async def create(**kwargs):
        calls.update(kwargs)
        if fail:
            raise fail
        return SimpleNamespace(
            content=[Block(b) for b in (blocks or [{"type": "text", "text": "Checking."},
                                                   {"type": "tool_use", "id": "toolu_1", "name": "get_bills", "input": {}}])],
            stop_reason="tool_use", model=model, usage=SimpleNamespace(to_dict=lambda: {"input_tokens": 10}),
        )

    stub = SimpleNamespace(create=create)
    provider.client = cast(anthropic.AsyncAnthropic, SimpleNamespace(messages=stub, beta=SimpleNamespace(messages=stub),
                                                                     close=lambda: None))
    return provider, calls


async def test_anthropic_request_shape_and_fallback():
    provider, calls = stub_provider()
    result = await provider.invoke(system="sys", messages=[{"role": "user", "content": "hi"}], tools=TOOLS)
    assert calls["model"] == "claude-opus-5" and calls["thinking"] == {"type": "adaptive"}
    assert calls["betas"] == [FALLBACK_BETA] and calls["fallbacks"] == "default"
    assert calls["tools"][0] == {"name": "get_bills", "description": "List bills", "input_schema": {"type": "object", "properties": {}}}
    assert result.tool_calls[0].name == "get_bills" and result.usage == {"input_tokens": 10}


async def test_anthropic_plan_call_is_tool_free_and_low_effort():
    provider, calls = stub_provider(model="claude-sonnet-5")
    await provider.invoke(system="plan", messages=[{"role": "user", "content": "x"}], tools=[], purpose="plan")
    assert "tools" not in calls and calls["output_config"] == {"effort": "low"} and "fallbacks" not in calls


@pytest.mark.parametrize("exc,retryable", [
    (anthropic.RateLimitError("slow down", response=httpx.Response(429, request=httpx.Request("POST", "http://x")), body=None), True),
    (anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=httpx.Request("POST", "http://x")), body=None), False),
    (anthropic.APIConnectionError(request=httpx.Request("POST", "http://x")), True),
])
async def test_anthropic_errors_become_safe_llm_errors(exc, retryable):
    provider, _ = stub_provider(fail=exc)
    with pytest.raises(LLMError) as info:
        await provider.invoke(system="", messages=[{"role": "user", "content": "x"}], tools=[])
    assert info.value.retryable is retryable
    assert "bad key" not in info.value.message and "slow down" not in info.value.message


def test_mid_output_fallback_blocks_are_sanitized():
    blocks = [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "partial"},
              {"type": "tool_use", "id": "t0", "name": "x", "input": {}},
              {"type": "fallback", "from": {"model": "a"}, "to": {"model": "b"}},
              {"type": "text", "text": "continued"}, {"type": "tool_use", "id": "t1", "name": "y", "input": {}}]
    out = sanitize_fallback_content(blocks)
    assert [b["type"] for b in out] == ["text", "text", "tool_use"] and out[-1]["id"] == "t1"
    assert sanitize_fallback_content(blocks[:3]) == blocks[:3]
