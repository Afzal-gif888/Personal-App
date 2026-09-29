"""The Anthropic provider, exercised against a stub client (no network)."""

from types import SimpleNamespace
from typing import cast

import anthropic
import httpx2
import pytest

from app.core.config import Settings, get_settings
from app.llm import LLMError, ToolSpec
from app.llm.anthropic_provider import FALLBACK_BETA, AnthropicProvider


class Block(dict):
    def to_dict(self):
        return dict(self)


def fake_response(*blocks, stop_reason="end_turn"):
    usage = SimpleNamespace(to_dict=lambda: {"input_tokens": 10, "output_tokens": 5})
    return SimpleNamespace(content=[Block(b) for b in blocks], stop_reason=stop_reason, model="claude-opus-5", usage=usage)


def make_provider(**overrides):
    settings = Settings(llm_provider="anthropic", llm_api_key="test-key", **overrides)
    provider = AnthropicProvider(settings)
    calls = {}

    def create(**kwargs):
        calls.update(kwargs)
        return fake_response(
            {"type": "text", "text": "Checking."},
            {"type": "tool_use", "id": "toolu_1", "name": "list_tasks", "input": {"status": "open"}},
            stop_reason="tool_use",
        )

    stub = SimpleNamespace(create=create)
    provider.client = cast(anthropic.Anthropic, SimpleNamespace(messages=stub, beta=SimpleNamespace(messages=stub)))
    return provider, calls


TOOLS = [ToolSpec("list_tasks", "List tasks", {"type": "object", "properties": {}})]


def test_default_model_uses_server_side_refusal_fallback():
    provider, calls = make_provider()
    resp = provider.complete(system="sys", messages=[{"role": "user", "content": "hi"}], tools=TOOLS)
    assert calls["model"] == "claude-opus-5"
    assert calls["betas"] == [FALLBACK_BETA] and calls["fallbacks"] == "default"
    assert calls["tools"][0] == {"name": "list_tasks", "description": "List tasks", "input_schema": TOOLS[0].input_schema}
    assert resp.stop_reason == "tool_use" and resp.text == "Checking."
    assert resp.tool_uses[0].name == "list_tasks" and resp.tool_uses[0].input == {"status": "open"}


def test_other_models_and_opt_out_skip_fallback():
    provider, calls = make_provider(llm_model="claude-sonnet-5")
    provider.complete(system="s", messages=[], tools=TOOLS)
    assert "fallbacks" not in calls
    provider, calls = make_provider(llm_refusal_fallback=False)
    provider.complete(system="s", messages=[], tools=TOOLS)
    assert "fallbacks" not in calls and "betas" not in calls


def test_api_errors_become_user_safe_llm_errors():
    provider, _ = make_provider()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

    def rate_limited(**_):
        raise anthropic.RateLimitError("slow down", response=httpx2.Response(429, request=request), body=None)

    provider.client.beta.messages.create = rate_limited
    with pytest.raises(LLMError) as exc:
        provider.complete(system="s", messages=[], tools=TOOLS)
    assert exc.value.retryable and "busy" in exc.value.message


def test_no_llm_configured_is_an_error_not_a_fake_assistant(monkeypatch):
    from app.llm import UnconfiguredProvider, get_provider

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_core_mode", "local")
    monkeypatch.setattr(settings, "llm_provider", "")
    get_provider.cache_clear()
    try:
        provider = get_provider()
        assert isinstance(provider, UnconfiguredProvider)
        with pytest.raises(LLMError, match="isn't set up yet"):
            provider.complete(system="", messages=[{"role": "user", "content": "hi"}], tools=[])
        with pytest.raises(ValueError):
            Settings.model_validate({"llm_provider": "mock"})
    finally:
        get_provider.cache_clear()
