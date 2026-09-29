"""OpenRouter provider (OpenAI-compatible chat completions), usable with free `:free` models.

    POST https://openrouter.ai/api/v1/chat/completions
    header: Authorization: Bearer <LLM_API_KEY>

The agent's transcript uses Messages API content blocks (text / tool_use / tool_result). This
provider translates them to chat-completions messages and back:

    user text                  ->  {"role": "user", "content": text}
    assistant text + tool_use  ->  {"role": "assistant", "content": text, "tool_calls": [...]}
    user tool_result           ->  {"role": "tool", "tool_call_id": id, "content": text}

Request economy (free models allow ~20 requests/minute and 50/day): backup models are passed in
OpenRouter's `models` array, so OpenRouter falls back *inside one request* instead of the app
making extra calls, and there is at most one retry, only for short waits.
"""

import asyncio
import itertools
import json
import logging
from typing import Any

import httpx

from app.config.settings import Settings
from app.llm.base import LLMError, LLMProvider, LLMResult, LLMToolSpec, Purpose

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
# Free models that support tool calling (checked against OpenRouter's model list).
DEFAULT_MODEL = "qwen/qwen3.8-27b:free"
DEFAULT_FALLBACK_MODELS = ("nvidia/nemotron-3-super-120b-a12b:free", "google/gemma-4-31b-it:free")
MAX_OUTPUT_TOKENS = 4096  # free models have small output limits; replies here are short anyway
MAX_RETRY_WAIT_SECONDS = 4.0
_SCHEMA_DROP = {"title", "default", "examples", "$defs"}
_ids = itertools.count(1)


def to_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Self-contained JSON Schema: `$ref`s inlined, Optional[X] collapsed to X, noise removed."""
    defs = schema.get("$defs", {})

    def convert(node: Any) -> Any:
        if isinstance(node, list):
            return [convert(v) for v in node]
        if not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            node = {**defs.get(ref.removeprefix("#/$defs/"), {}), **{k: v for k, v in node.items() if k != "$ref"}}
        options = node.get("anyOf")
        if options:
            non_null = [o for o in options if o.get("type") != "null"]
            if len(non_null) == 1:
                merged = {**non_null[0], **{k: v for k, v in node.items() if k == "description"}}
                return convert(merged)
        out = {}
        for key, value in node.items():
            if key in _SCHEMA_DROP:
                continue
            if key == "properties":
                out[key] = {name: convert(prop) for name, prop in value.items()}
            else:
                out[key] = convert(value)
        return out

    return convert(schema)


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    return "\n\n".join(b.get("text", "") for b in content or [] if b.get("type") == "text" and b.get("text"))


def to_chat_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}] if system else []
    for message in messages:
        role, content = message.get("role"), message.get("content")
        if role not in ("user", "assistant"):
            continue
        if isinstance(content, str):
            if content:
                out.append({"role": role, "content": content})
            continue
        blocks = content or []
        if role == "assistant":
            calls = [
                {"id": b["id"], "type": "function",
                 "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
                for b in blocks if b.get("type") == "tool_use"
            ]
            entry: dict[str, Any] = {"role": "assistant", "content": _text_of(blocks) or None}
            if calls:
                entry["tool_calls"] = calls
            if entry["content"] or calls:
                out.append(entry)
        else:
            for b in blocks:  # tool results must directly follow the assistant turn that asked for them
                if b.get("type") == "tool_result":
                    result = b.get("content")
                    out.append({"role": "tool", "tool_call_id": b.get("tool_use_id", ""),
                                "content": result if isinstance(result, str) else json.dumps(result)})
            text = _text_of(blocks)
            if text:
                out.append({"role": "user", "content": text})
    return out


def from_chat_response(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    blocks: list[dict[str, Any]] = []
    text = message.get("content")
    if isinstance(text, str) and text.strip():
        blocks.append({"type": "text", "text": text})
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(args, dict):
                raise ValueError
        except ValueError:
            args = {"_malformed_arguments": str(raw)[:500]}  # reported back to the model as a tool error
        blocks.append({"type": "tool_use", "id": call.get("id") or f"call_{next(_ids)}", "name": fn.get("name", ""), "input": args})
    reason = choice.get("finish_reason") or "stop"
    if any(b["type"] == "tool_use" for b in blocks):
        return blocks, "tool_use"
    if reason == "length":
        return blocks, "max_tokens"
    if reason == "content_filter":
        return blocks, "refusal"
    return blocks, "end_turn"


class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.model = settings.llm_model or DEFAULT_MODEL
        configured = [m.strip() for m in settings.llm_fallback_models.split(",") if m.strip()]
        self.fallbacks = [m for m in dict.fromkeys(configured or DEFAULT_FALLBACK_MODELS) if m != self.model]
        self.max_tokens = min(settings.llm_max_tokens, MAX_OUTPUT_TOKENS)
        self._http = httpx.AsyncClient(
            base_url=(settings.llm_base_url or DEFAULT_BASE_URL).rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}",
                # Optional attribution headers OpenRouter uses to identify the app.
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "It's Personal",
            },
            timeout=settings.llm_timeout_seconds,
            transport=transport,
        )

    async def invoke(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[LLMToolSpec], purpose: Purpose = "act"
    ) -> LLMResult:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": to_chat_messages(system, messages),
            "max_tokens": self.max_tokens,
        }
        if self.fallbacks:
            body["models"] = [self.model, *self.fallbacks]  # OpenRouter tries these in order, in one request
        if tools:
            body["tools"] = [
                {"type": "function", "function": {"name": t.name, "description": t.description,
                                                  "parameters": to_openai_schema(t.input_schema)}}
                for t in tools
            ]
            body["tool_choice"] = "auto"
        data = await self._post(body)
        content, stop_reason = from_chat_response(data)
        return LLMResult(content=content, stop_reason=stop_reason, model=data.get("model") or self.model,
                         usage=data.get("usage") or {})

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):  # at most one retry, and only for a short suggested wait
            try:
                resp = await self._http.post("/chat/completions", json=body)
            except httpx.TimeoutException:
                raise LLMError("The assistant took too long to respond. Please try again.", retryable=True)
            except httpx.HTTPError:
                raise LLMError("Couldn't reach the assistant service. Please try again.", retryable=True)
            try:
                data = resp.json()
            except ValueError:
                data = {}
            # OpenRouter can report an upstream failure inside a 200 body.
            error = data.get("error") if isinstance(data, dict) else None
            status = resp.status_code if not (resp.is_success and error) else int((error or {}).get("code") or 502)
            if resp.is_success and not error and isinstance(data, dict) and data.get("choices"):
                return data
            if status in (429, 502, 503) and attempt == 0:
                wait = _retry_after(resp)
                if wait is not None and wait <= MAX_RETRY_WAIT_SECONDS:
                    await asyncio.sleep(wait)
                    continue
            logger.warning("OpenRouter API error", extra={"status": status})  # never the body: it can echo the prompt
            if status == 401:
                raise LLMError("The assistant is misconfigured (the OpenRouter API key was rejected).")
            if status == 402:
                raise LLMError("The OpenRouter account has no credits left for this model. Use a ':free' model or add credits.")
            if status == 429:
                raise LLMError("The assistant has reached its usage limit for now. Please try again in a minute.",
                               retryable=True, rate_limited=True)
            if status == 404:
                raise LLMError("The assistant is misconfigured (the selected model isn't available). Check LLM_MODEL.")
            if status in (400, 413, 422):
                raise LLMError("The assistant couldn't process that request.")
            raise LLMError("The assistant is busy right now. Please try again in a minute.", retryable=True)
        raise LLMError("The assistant is busy right now. Please try again in a minute.", retryable=True)  # pragma: no cover

    async def aclose(self) -> None:
        await self._http.aclose()


def _retry_after(resp: httpx.Response) -> float | None:
    try:
        return float(resp.headers.get("retry-after", ""))
    except ValueError:
        return None
