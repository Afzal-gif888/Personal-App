"""Google Gemini provider (Gemini API `generateContent`), usable with a free-tier AI Studio key.

    POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    header: x-goog-api-key: <LLM_API_KEY>

The agent's transcript uses Messages API content blocks (text / tool_use / tool_result). This
provider translates them to Gemini `contents` on the way out and back on the way in:

    user text / tool_result    ->  role "user",  parts: text / functionResponse {id, name, response}
    assistant text / tool_use  ->  role "model", parts: text / functionCall {id, name, args}

Gemini may attach a `thoughtSignature` to parts of its reply (for example a functionCall) and
requires them back unchanged on the next turn. Every block built from a Gemini reply therefore
keeps the raw part under `gemini_part`, and model turns are re-sent from those raw parts verbatim.
"""

import asyncio
import itertools
import json
import logging
import re
import time
from typing import Any

import httpx

from app.config.settings import Settings
from app.llm.base import LLMError, LLMProvider, LLMResult, LLMToolSpec, Purpose

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.8-flash"  # gemini-2.5-* is closed to new API users
# Free-tier models tried in order when the configured one is overloaded or out of quota.
DEFAULT_FALLBACK_MODELS = ("gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash")
MAX_RETRIES = 1  # per model, for 429 and 5xx, before moving to the next model
MAX_RETRY_WAIT_SECONDS = 4.0  # longer waits (free-tier quota resets) move on instead of hanging the run
ATTEMPT_TIMEOUT_SECONDS = 40.0  # an overloaded model can hang; give up on it and try the next
STICKY_SECONDS = 300.0  # keep using the model that worked, so thought signatures stay valid

# Gemini function schemas accept an OpenAPI subset; other JSON Schema keywords are dropped.
_SCHEMA_KEYS = {"type", "format", "description", "nullable", "enum", "properties", "required", "items",
                "minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength", "pattern"}
# Google's documented placeholder for function calls whose signature isn't valid for the target model
# (calls from another model or provider). Without it Gemini 3 rejects the history with a 400.
SKIP_SIGNATURE = "skip_thought_signature_validator"
_REFUSAL_REASONS = {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY"}
_ids = itertools.count(1)


def to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic JSON Schema -> the OpenAPI subset Gemini accepts (refs inlined, Optional -> nullable)."""
    defs = schema.get("$defs", {})

    def convert(node: Any) -> Any:
        if not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            node = {**defs.get(ref.removeprefix("#/$defs/"), {}), **{k: v for k, v in node.items() if k != "$ref"}}
        options = node.get("anyOf") or node.get("oneOf")
        if options:
            non_null = [o for o in options if o.get("type") != "null"]
            chosen = dict(non_null[0]) if non_null else {"type": "string"}
            if node.get("description"):  # the field's description, plus any format hint the option adds
                chosen["description"] = node["description"]
            merged = convert(chosen)
            if len(non_null) < len(options):
                merged["nullable"] = True
            return merged
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key not in _SCHEMA_KEYS:
                continue
            if key == "properties":
                out[key] = {name: convert(prop) for name, prop in value.items()}
            elif key == "items":
                out[key] = convert(value)
            elif key == "format":
                if value == "date-time":
                    out[key] = value
                else:  # e.g. date/time: keep the hint for the model, not as a constraint
                    out["description"] = f"{node.get('description', '')} (format: {value})".strip()
            elif key == "description" and "description" in out:
                continue
            else:
                out[key] = value
        if "enum" in out and "type" not in out:
            out["type"] = "string"
        return out

    return convert(schema)


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    return "\n\n".join(b.get("text", "") for b in content or [] if b.get("type") == "text" and b.get("text"))


def _response_object(content: Any, is_error: bool) -> dict[str, Any]:
    raw = content if isinstance(content, str) else _text_of(content)
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        value = raw
    if not isinstance(value, dict):
        value = {"result": value}
    return {"error": value} if is_error and "error" not in value else value


def to_gemini_contents(messages: list[dict[str, Any]], model: str | None = None) -> list[dict[str, Any]]:
    """Translate the transcript for `model`. Gemini's own parts (with their thought signatures) are
    re-sent verbatim only to the model that produced them; otherwise function calls carry the
    documented placeholder signature, since another model's signature is rejected as corrupted."""
    contents: list[dict[str, Any]] = []
    names: dict[str, str] = {}  # tool_use id -> function name (functionResponse needs the name)

    def add(role: str, parts: list[dict[str, Any]]) -> None:
        if not parts:
            return
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"].extend(parts)
        else:
            contents.append({"role": role, "parts": parts})

    for message in messages:
        role, content = message.get("role"), message.get("content")
        if role not in ("user", "assistant"):
            continue
        if isinstance(content, str):
            add("model" if role == "assistant" else "user", [{"text": content}] if content else [])
            continue
        blocks = content or []
        if role == "assistant":
            for b in blocks:
                if b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
            raw_blocks = [b for b in blocks if "gemini_part" in b or b.get("type") == "gemini_part"]
            same_model = model is None or all(b.get("gemini_model") == model for b in raw_blocks)
            if raw_blocks and same_model:
                raw = [b["gemini_part"] if "gemini_part" in b else b.get("part") for b in raw_blocks]
                add("model", [p for p in raw if p])  # re-send Gemini's own parts, signatures included
                continue
            parts: list[dict[str, Any]] = []
            for b in blocks:  # thought parts from another model are dropped
                if b.get("type") == "text" and b.get("text"):
                    parts.append({"text": b["text"]})
                elif b.get("type") == "tool_use":
                    parts.append({"functionCall": {"id": b["id"], "name": b["name"], "args": b.get("input") or {}},
                                  "thoughtSignature": SKIP_SIGNATURE})
            add("model", parts)
        else:
            parts = []
            for b in blocks:
                if b.get("type") == "tool_result":
                    call_id = b.get("tool_use_id", "")
                    parts.append({"functionResponse": {
                        "id": call_id, "name": names.get(call_id, "tool"),
                        "response": _response_object(b.get("content"), bool(b.get("is_error"))),
                    }})
                elif b.get("type") == "text" and b.get("text"):
                    parts.append({"text": b["text"]})
            add("user", parts)
    return contents


def from_gemini_response(data: dict[str, Any], model: str = "") -> tuple[list[dict[str, Any]], str]:
    """Response -> (content blocks, stop_reason). Blocks remember which model produced them."""
    candidates = data.get("candidates") or []
    if not candidates:
        if (data.get("promptFeedback") or {}).get("blockReason"):
            return [], "refusal"
        return [], "end_turn"
    candidate = candidates[0]
    blocks: list[dict[str, Any]] = []
    has_call = False
    for part in (candidate.get("content") or {}).get("parts") or []:
        if "functionCall" in part:
            call = part["functionCall"]
            has_call = True
            args = call.get("args")
            blocks.append({"type": "tool_use", "id": call.get("id") or f"gemini_call_{next(_ids)}",
                           "name": call.get("name", ""), "input": args if isinstance(args, dict) else {},
                           "gemini_part": part, "gemini_model": model})
        elif "text" in part and not part.get("thought"):
            blocks.append({"type": "text", "text": part["text"], "gemini_part": part, "gemini_model": model})
        else:  # thought summaries or signature-only parts: keep for the round trip, never shown
            blocks.append({"type": "gemini_part", "part": part, "gemini_model": model})
    reason = candidate.get("finishReason", "STOP")
    if has_call:
        return blocks, "tool_use"
    if reason == "MAX_TOKENS":
        return blocks, "max_tokens"
    if reason in _REFUSAL_REASONS:
        return blocks, "refusal"
    if reason == "MALFORMED_FUNCTION_CALL":
        return [{"type": "text", "text": "I couldn't complete that action. Could you rephrase the request?"}], "end_turn"
    return blocks, "end_turn"


def _retry_delay(resp: httpx.Response) -> float | None:
    header = resp.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    try:
        for detail in resp.json().get("error", {}).get("details", []):
            if m := re.fullmatch(r"(\d+(?:\.\d+)?)s", str(detail.get("retryDelay", ""))):
                return float(m.group(1))
    except (ValueError, AttributeError):
        pass
    return None


def _error_status(resp: httpx.Response) -> tuple[str, set[str]]:
    try:
        err = resp.json().get("error", {})
        reasons = {str(d.get("reason")) for d in err.get("details", []) if d.get("reason")}
        return str(err.get("status", "")), reasons
    except (ValueError, AttributeError):
        return "", set()


class _Unavailable(Exception):
    """This model can't serve the request right now; another model may."""

    def __init__(self, reason: str, *, rate_limited: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.rate_limited = rate_limited


class GeminiProvider(LLMProvider):
    """Calls Gemini with an ordered model chain.

    Free-tier capacity varies by model and by minute (503 "high demand", hanging requests, per-model
    quotas). When the current model is unavailable the request moves to the next model in the
    chain, and the model that worked stays preferred for a few minutes so a conversation keeps its
    thought signatures valid. Auth and request errors fail immediately: another model would not help.
    """

    name = "gemini"

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.model = settings.llm_model or DEFAULT_MODEL
        configured = [m.strip() for m in settings.llm_fallback_models.split(",") if m.strip()]
        fallbacks = configured or list(DEFAULT_FALLBACK_MODELS)
        self.models = [self.model] + [m for m in dict.fromkeys(fallbacks) if m != self.model]
        self.max_tokens = settings.llm_max_tokens
        self.budget_seconds = settings.llm_timeout_seconds
        self._preferred: str | None = None
        self._preferred_until = 0.0
        self._http = httpx.AsyncClient(
            base_url=(settings.llm_base_url or DEFAULT_BASE_URL).rstrip("/"),
            headers={"x-goog-api-key": settings.llm_api_key.get_secret_value()},
            timeout=min(settings.llm_timeout_seconds, ATTEMPT_TIMEOUT_SECONDS),
            transport=transport,
        )

    def model_order(self) -> list[str]:
        if self._preferred and time.monotonic() < self._preferred_until:
            return [self._preferred] + [m for m in self.models if m != self._preferred]
        return list(self.models)

    def _body(self, model: str, system: str, messages: list[dict[str, Any]], tools: list[LLMToolSpec]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contents": to_gemini_contents(messages, model),
            "generationConfig": {"maxOutputTokens": self.max_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = [{"functionDeclarations": [
                {"name": t.name, "description": t.description, "parameters": to_gemini_schema(t.input_schema)}
                for t in tools
            ]}]
            body["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}
        return body

    async def invoke(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[LLMToolSpec], purpose: Purpose = "act"
    ) -> LLMResult:
        deadline = time.monotonic() + self.budget_seconds
        failures: list[_Unavailable] = []
        for model in self.model_order():
            if time.monotonic() >= deadline:
                break
            try:
                data = await self._post(model, self._body(model, system, messages, tools))
            except _Unavailable as exc:
                failures.append(exc)
                logger.warning("Gemini model unavailable, trying the next one", extra={"model": model, "reason": exc.reason})
                continue
            if model != self.models[0] or self._preferred:
                self._preferred, self._preferred_until = model, time.monotonic() + STICKY_SECONDS
            content, stop_reason = from_gemini_response(data, model)
            return LLMResult(content=content, stop_reason=stop_reason, model=model, usage=data.get("usageMetadata") or {})
        if failures and all(f.reason == "model_not_found" for f in failures):
            logger.error("No configured Gemini model is available to this key", extra={"models": self.models})
            raise LLMError("The assistant is misconfigured. Please contact the administrator.")
        if failures and all(f.rate_limited for f in failures):
            raise LLMError("The assistant has reached its usage limit for now. Please try again in a minute.",
                           retryable=True, rate_limited=True)
        raise LLMError("The assistant is busy right now (the AI service is overloaded). Please try again in a minute.",
                       retryable=True)

    async def _post(self, model: str, body: dict[str, Any]) -> dict[str, Any]:
        path = f"/models/{model}:generateContent"
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await self._http.post(path, json=body)
            except httpx.TimeoutException:
                raise _Unavailable("timeout")
            except httpx.HTTPError:
                raise LLMError("Couldn't reach the assistant service. Please try again.", retryable=True)
            if resp.is_success:
                try:
                    data = resp.json()
                except ValueError:
                    raise LLMError("The assistant service sent an invalid response.")
                if not isinstance(data, dict):
                    raise LLMError("The assistant service sent an invalid response.")
                return data

            status = resp.status_code
            err_status, reasons = _error_status(resp)
            if status == 429 or status >= 500:
                wait = _retry_delay(resp)
                wait = 1.0 * (2**attempt) if wait is None else wait
                if attempt < MAX_RETRIES and wait <= MAX_RETRY_WAIT_SECONDS:
                    await asyncio.sleep(wait)
                    continue
                raise _Unavailable(err_status or str(status), rate_limited=status == 429)
            # Log codes only: error messages can echo parts of the request.
            logger.warning("Gemini API error", extra={"model": model, "status": status, "error_status": err_status,
                                                      "reasons": sorted(reasons)})
            if status in (401, 403) or "API_KEY_INVALID" in reasons:
                raise LLMError("The assistant is misconfigured. Please contact the administrator.")
            if status == 404:  # this model is not available to the key; another one may be
                raise _Unavailable("model_not_found")
            if status in (400, 422):
                raise LLMError("The assistant couldn't process that request.")
            raise LLMError("The assistant is temporarily unavailable. Please try again.", retryable=True)
        raise _Unavailable("retries_exhausted")  # pragma: no cover

    async def aclose(self) -> None:
        await self._http.aclose()
