"""FreeLLMAPI provider unit tests with stubbed HTTP (no network needed)."""

import json
import httpx
import pytest

from app.llm.base import LLMError, LLMToolSpec
from app.llm.factory import create_llm_provider
from app.llm.freellmapi import FreeLLMAPIProvider
from tests.conftest import make_settings

KEY = "freellmapi-test-key-12345"
TOOLS = [LLMToolSpec("get_bills", "List bills", {"type": "object", "properties": {"due_within_days": {"type": "integer"}}})]
USER = [{"role": "user", "content": "What bills are due?"}]


def settings(**kw):
    return make_settings(
        llm_provider="freellmapi",
        freellmapi_api_key=KEY,
        freellmapi_base_url="http://127.0.0.1:31415/v1",
        freellmapi_model="auto",
        **kw,
    )


def reply(text=None, calls=(), finish="stop", model="auto"):
    message = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = [
            {"id": cid, "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
            for cid, n, a in calls
        ]
        finish = "tool_calls"
    return {
        "id": "chatcmpl-test-1",
        "model": model,
        "choices": [{"message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8},
    }


class Stub:
    def __init__(self, *responses):
        self.queue = list(responses)
        self.bodies = []
        self.headers = []

    def provider(self, **kw):
        def handle(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/chat/completions"
            self.bodies.append(json.loads(request.content))
            self.headers.append(request.headers)
            item = self.queue.pop(0)
            if isinstance(item, tuple):
                return httpx.Response(item[0], json=item[1], headers=item[2] if len(item) > 2 else {})
            return httpx.Response(200, json=item)

        return FreeLLMAPIProvider(settings(**kw), transport=httpx.MockTransport(handle))


def test_factory_and_no_key():
    p = create_llm_provider(settings())
    assert p.name == "freellmapi"
    unconf = create_llm_provider(make_settings(llm_provider="freellmapi"))
    assert unconf.name == "unconfigured"


@pytest.mark.asyncio
async def test_text_invoke():
    stub = Stub(reply(text="You have no bills due."))
    p = stub.provider()
    res = await p.invoke(system="You are a personal assistant.", messages=USER, tools=[])
    assert res.text == "You have no bills due."
    assert res.stop_reason == "end_turn"
    assert stub.headers[0]["authorization"] == f"Bearer {KEY}"
    assert stub.bodies[0]["model"] == "auto"
    assert stub.bodies[0]["messages"][0] == {"role": "system", "content": "You are a personal assistant."}
    assert stub.bodies[0]["messages"][1] == {"role": "user", "content": "What bills are due?"}


@pytest.mark.asyncio
async def test_tool_call_invoke():
    stub = Stub(reply(calls=[("call_1", "get_bills", {"due_within_days": 7})]))
    p = stub.provider()
    res = await p.invoke(system="", messages=USER, tools=TOOLS)
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "get_bills"
    assert res.tool_calls[0].input == {"due_within_days": 7}
    assert res.stop_reason == "tool_use"


@pytest.mark.asyncio
async def test_error_handling_401():
    stub = Stub((401, {"error": {"message": "Invalid API key"}}))
    p = stub.provider()
    with pytest.raises(LLMError, match="FreeLLMAPI API key was rejected"):
        await p.invoke(system="", messages=USER, tools=[])
