"""Gemini provider against a stubbed generateContent API (no key or network needed)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llm.base import LLMError, LLMToolSpec
from app.llm.factory import create_llm_provider
from app.llm.gemini import GeminiProvider, from_gemini_response, to_gemini_contents, to_gemini_schema
from app.main import create_app
from app.schemas.agent import RunStatus
from tests.conftest import SERVICE_TOKEN, Harness, make_settings
from tests.mock_llm import MockLLMProvider

KEY = "AIza-test-key-123"


def gemini_settings(**kw):
    return make_settings(llm_provider="gemini", llm_api_key=KEY, **kw)


def text_reply(text: str, reason: str = "STOP") -> dict:
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": reason}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}, "modelVersion": "gemini-3.8-flash"}


def call_reply(*calls: tuple[str, str, dict], signature: str | None = "sig-abc") -> dict:
    parts = []
    for i, (cid, name, args) in enumerate(calls):
        part: dict = {"functionCall": {"id": cid, "name": name, "args": args}}
        if signature and i == 0:
            part["thoughtSignature"] = signature
        parts.append(part)
    return {"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}],
            "modelVersion": "gemini-3.8-flash"}


class StubGemini:
    """Serves queued responses (dicts, or (status, body, headers) tuples) and records requests."""

    def __init__(self, *responses) -> None:
        self.queue = list(responses)
        self.requests: list[dict] = []
        self.paths: list[str] = []
        self.headers: list[httpx.Headers] = []

    def transport(self) -> httpx.MockTransport:
        def handle(request: httpx.Request) -> httpx.Response:
            self.paths.append(request.url.path)
            self.requests.append(json.loads(request.content))
            self.headers.append(request.headers)
            item = self.queue.pop(0)
            if isinstance(item, tuple):
                status, body, headers = item
                return httpx.Response(status, json=body, headers=headers)
            return httpx.Response(200, json=item)

        return httpx.MockTransport(handle)

    def provider(self, **kw) -> GeminiProvider:
        return GeminiProvider(gemini_settings(**kw), transport=self.transport())


TOOLS = [LLMToolSpec("get_bills", "List bills", {"type": "object", "properties": {"due_within_days": {"type": "integer"}}})]
USER = [{"role": "user", "content": "What bills are due?"}]


def test_factory_selects_gemini_and_falls_back_without_key():
    assert create_llm_provider(gemini_settings()).name == "gemini"
    assert create_llm_provider(make_settings(llm_provider="gemini")).name == "unconfigured"
    with pytest.raises(RuntimeError, match="LLM_PROVIDER=gemini requires LLM_API_KEY"):
        create_llm_provider(make_settings(app_env="production", agent_core_service_token="x", llm_provider="gemini"))


def test_schema_conversion():
    schema = {
        "type": "object", "additionalProperties": False, "title": "X",
        "properties": {
            "key": {"$ref": "#/$defs/Key"},
            "due": {"anyOf": [{"type": "string", "format": "date"}, {"type": "null"}], "default": None, "description": "Due"},
            "n": {"type": "integer", "minimum": 0, "title": "N"},
            "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        },
        "required": ["key"],
        "$defs": {"Key": {"title": "Key", "type": "string", "enum": ["a", "b"]}},
    }
    assert to_gemini_schema(schema) == {
        "type": "object", "required": ["key"],
        "properties": {
            "key": {"type": "string", "enum": ["a", "b"]},
            "due": {"type": "string", "description": "Due (format: date)", "nullable": True},
            "n": {"type": "integer", "minimum": 0},
            "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        },
    }


def test_transcript_translation_fresh_blocks():
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "What bills are due?"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "Checking."},
            {"type": "tool_use", "id": "c1", "name": "get_bills", "input": {"due_within_days": 7}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "c1", "content": '{"items": [], "total": 0}'},
            {"type": "tool_result", "tool_use_id": "c2", "content": '{"error": "boom"}', "is_error": True},
        ]},
    ]
    assert to_gemini_contents(messages) == [
        {"role": "user", "parts": [{"text": "Hi"}]},
        {"role": "model", "parts": [{"text": "Hello!"}]},
        {"role": "user", "parts": [{"text": "What bills are due?"}]},
        {"role": "model", "parts": [{"text": "Checking."},
                                    {"functionCall": {"id": "c1", "name": "get_bills", "args": {"due_within_days": 7}},
                                     "thoughtSignature": "skip_thought_signature_validator"}]},
        {"role": "user", "parts": [
            {"functionResponse": {"id": "c1", "name": "get_bills", "response": {"items": [], "total": 0}}},
            {"functionResponse": {"id": "c2", "name": "tool", "response": {"error": "boom"}}},
        ]},
    ]


def test_thought_signatures_round_trip_unchanged():
    reply = call_reply(("c1", "get_bills", {"due_within_days": 7}))
    reply["candidates"][0]["content"]["parts"].insert(0, {"text": "planning...", "thought": True, "thoughtSignature": "t-sig"})
    blocks, stop = from_gemini_response(reply)
    assert stop == "tool_use" and [b["type"] for b in blocks] == ["gemini_part", "tool_use"]
    resent = to_gemini_contents([*USER, {"role": "assistant", "content": blocks}])
    assert resent[1] == {"role": "model", "parts": reply["candidates"][0]["content"]["parts"]}  # byte-for-byte


def test_response_parsing():
    blocks, stop = from_gemini_response(text_reply("All paid."))
    assert stop == "end_turn" and blocks[0]["type"] == "text" and blocks[0]["text"] == "All paid."
    assert from_gemini_response(text_reply("cut", "MAX_TOKENS"))[1] == "max_tokens"
    assert from_gemini_response(text_reply("", "SAFETY"))[1] == "refusal"
    assert from_gemini_response({"promptFeedback": {"blockReason": "SAFETY"}}) == ([], "refusal")
    malformed = from_gemini_response({"candidates": [{"content": {"parts": []}, "finishReason": "MALFORMED_FUNCTION_CALL"}]})
    assert malformed[1] == "end_turn" and "rephrase" in malformed[0][0]["text"]
    no_id = from_gemini_response({"candidates": [{"content": {"parts": [{"functionCall": {"name": "get_bills", "args": {}}}]}}]})
    assert no_id[0][0]["id"].startswith("gemini_call_")


async def test_request_shape():
    stub = StubGemini(call_reply(("c1", "get_bills", {"due_within_days": 7})))
    result = await stub.provider().invoke(system="be helpful", messages=USER, tools=TOOLS)
    body = stub.requests[0]
    assert stub.paths[0] == "/v1beta/models/gemini-3.8-flash:generateContent"
    assert stub.headers[0]["x-goog-api-key"] == KEY and "authorization" not in stub.headers[0]
    assert body["systemInstruction"] == {"parts": [{"text": "be helpful"}]}
    assert body["tools"][0]["functionDeclarations"][0]["name"] == "get_bills"
    assert body["toolConfig"] == {"functionCallingConfig": {"mode": "AUTO"}}
    assert body["generationConfig"]["maxOutputTokens"] == 16000
    assert result.tool_calls[0].input == {"due_within_days": 7} and result.stop_reason == "tool_use"


async def test_model_override_and_tool_free_calls():
    stub = StubGemini(text_reply("1. Check bills"))
    result = await stub.provider(llm_model="gemini-3.5-flash").invoke(system="", messages=USER, tools=[], purpose="plan")
    assert stub.paths[0].endswith("/gemini-3.5-flash:generateContent")
    assert "tools" not in stub.requests[0] and "systemInstruction" not in stub.requests[0]
    assert result.text == "1. Check bills"


async def test_short_rate_limit_is_retried(monkeypatch):
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("app.llm.gemini.asyncio.sleep", fake_sleep)
    quota = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                       "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "2s"}]}}
    stub = StubGemini((429, quota, {}), text_reply("done"))
    assert (await stub.provider().invoke(system="", messages=USER, tools=[])).text == "done"
    assert waits == [2.0]


async def test_long_quota_wait_fails_fast(monkeypatch):
    monkeypatch.setattr("app.llm.gemini.asyncio.sleep", _fail_if_called)
    quota = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                       "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "45s"}]}}
    stub = StubGemini(*[(429, quota, {})] * 4)  # every model in the chain is out of quota
    with pytest.raises(LLMError) as info:
        await stub.provider().invoke(system="", messages=USER, tools=[])
    assert info.value.rate_limited and "usage limit" in info.value.message
    assert [p.split("/")[-1] for p in stub.paths] == [f"{m}:generateContent" for m in
                                                      ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash")]


@pytest.mark.parametrize("status,body,message", [
    (400, {"error": {"status": "INVALID_ARGUMENT", "details": [{"reason": "API_KEY_INVALID"}]}}, "misconfigured"),
    (403, {"error": {"status": "PERMISSION_DENIED"}}, "misconfigured"),
    (404, {"error": {"status": "NOT_FOUND"}}, "misconfigured"),
    (400, {"error": {"status": "INVALID_ARGUMENT", "message": "secret prompt text"}}, "couldn't process"),
])
async def test_errors_are_safe(status, body, message):
    stub = StubGemini(*[(status, body, {})] * 4)  # 404 is per-model, so every model in the chain returns it
    with pytest.raises(LLMError) as info:
        await stub.provider().invoke(system="", messages=USER, tools=[])
    assert message in info.value.message and "secret" not in info.value.message


async def test_full_agent_run_with_gemini(backend):
    stub = StubGemini(
        call_reply(("c1", "get_bills", {"due_within_days": 7})),
        text_reply("Your electricity bill of ₹1,200 is due in 3 days."),
    )
    h = Harness(backend, gemini_settings(), llm=stub.provider())
    r = await h.run("What bills are due this week?")
    assert r.status == RunStatus.COMPLETED and [t.name for t in r.tool_calls] == ["get_bills"]
    assert r.response == "Your electricity bill of ₹1,200 is due in 3 days."
    second = stub.requests[1]["contents"]
    assert second[-2]["parts"][0]["thoughtSignature"] == "sig-abc"  # signature sent back unchanged
    response = second[-1]["parts"][0]["functionResponse"]
    assert response["name"] == "get_bills" and response["response"]["items"][0]["title"] == "Electricity bill"


async def test_planning_call_can_be_disabled(backend):
    with_plan, without_plan = MockLLMProvider(), MockLLMProvider()
    await Harness(backend, make_settings(), llm=with_plan).run("What do I need to take care of this week?")
    assert any(c["purpose"] == "plan" for c in with_plan.calls)
    r = await Harness(backend, make_settings(llm_planning=False), llm=without_plan).run("What do I need to take care of this week?")
    assert not any(c["purpose"] == "plan" for c in without_plan.calls) and r.status == RunStatus.COMPLETED


def test_backend_compat_endpoint_uses_gemini(backend):
    stub = StubGemini(call_reply(("c1", "get_bills", {})))
    app = create_app(gemini_settings(agent_core_service_token=SERVICE_TOKEN), llm=stub.provider(),
                     backend_transport=backend.transport())
    with TestClient(app) as client:
        r = client.post("/v1/complete", headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
                        json={"system": "s", "messages": USER,
                              "tools": [{"name": "get_bills", "description": "d", "input_schema": {"type": "object"}}]})
        assert client.get("/ready").json()["checks"]["llm"] == "gemini"
    block = r.json()["content"][0]
    assert r.status_code == 200 and block["type"] == "tool_use" and block["name"] == "get_bills"
    assert block["gemini_part"]["thoughtSignature"] == "sig-abc"  # survives the backend round trip


async def _fail_if_called(_seconds):
    raise AssertionError("should not wait on a long quota reset")


async def test_overloaded_model_falls_back_and_stays_preferred(monkeypatch):
    monkeypatch.setattr("app.llm.gemini.asyncio.sleep", _no_sleep)
    busy = {"error": {"code": 503, "status": "UNAVAILABLE"}}
    stub = StubGemini((503, busy, {}), (503, busy, {}), text_reply("from 3.7"), text_reply("again 3.7"))
    provider = stub.provider()
    first = await provider.invoke(system="", messages=USER, tools=[])
    assert first.text == "from 3.7" and first.model == "gemini-3.7-flash"
    second = await provider.invoke(system="", messages=USER, tools=[])
    assert second.model == "gemini-3.7-flash"  # sticky: no new attempt on the overloaded model
    assert [p.split("/")[-1].split(":")[0] for p in stub.paths] == ["gemini-3.8-flash", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.7-flash"]


async def test_hanging_model_times_out_to_the_next():
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if "gemini-3.8-flash" in request.url.path:
            raise httpx.ReadTimeout("hung", request=request)
        return httpx.Response(200, json=text_reply("ok"))

    provider = GeminiProvider(gemini_settings(), transport=httpx.MockTransport(handle))
    assert (await provider.invoke(system="", messages=USER, tools=[])).model == "gemini-3.7-flash"
    assert len(calls) == 2


async def test_configured_fallbacks_and_all_busy(monkeypatch):
    monkeypatch.setattr("app.llm.gemini.asyncio.sleep", _no_sleep)
    busy = {"error": {"code": 503, "status": "UNAVAILABLE"}}
    stub = StubGemini(*[(503, busy, {})] * 4)
    provider = stub.provider(llm_model="gemini-3.6-flash", llm_fallback_models="gemini-3.5-flash")
    assert provider.models == ["gemini-3.6-flash", "gemini-3.5-flash"]
    with pytest.raises(LLMError) as info:
        await provider.invoke(system="", messages=USER, tools=[])
    assert "busy" in info.value.message and info.value.retryable and not info.value.rate_limited


def test_signatures_are_only_resent_to_the_model_that_made_them():
    blocks, _ = from_gemini_response(call_reply(("c1", "get_bills", {})), "gemini-3.8-flash")
    history = [*USER, {"role": "assistant", "content": blocks}]
    same = to_gemini_contents(history, "gemini-3.8-flash")[1]["parts"][0]
    other = to_gemini_contents(history, "gemini-3.7-flash")[1]["parts"][0]
    assert same["thoughtSignature"] == "sig-abc"
    assert other["thoughtSignature"] == "skip_thought_signature_validator"  # the real one would be "corrupted"


async def _no_sleep(_seconds):
    return None
