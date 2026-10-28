"""FreeLLMAPI provider (OpenAI-compatible chat completions API).

    POST {base_url}/chat/completions
    header: Authorization: Bearer <FREELLMAPI_API_KEY>

Uses OpenAI-compatible chat messages and tool-calling format.
"""

import asyncio
import json
import logging
from typing import Any

import httpx

from app.config.settings import Settings
from app.llm.base import LLMError, LLMProvider, LLMResult, LLMToolSpec, Purpose
from app.llm.openrouter import from_chat_response, to_chat_messages, to_openai_schema

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://127.0.0.1:31415/v1"
DEFAULT_MODEL = "auto"
MAX_RETRY_WAIT_SECONDS = 4.0


class FreeLLMAPIProvider(LLMProvider):
    name = "freellmapi"

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.model = settings.llm_model or settings.freellmapi_model or DEFAULT_MODEL
        base_url = (settings.llm_base_url or settings.freellmapi_base_url or DEFAULT_BASE_URL).rstrip("/")
        api_key = (
            settings.freellmapi_api_key.get_secret_value()
            or settings.llm_api_key.get_secret_value()
        )
        self.max_tokens = settings.llm_max_tokens
        self.base_url = base_url
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
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
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": to_openai_schema(t.input_schema),
                    },
                }
                for t in tools
            ]
            body["tool_choice"] = "auto"
        data = await self._post(body)
        content, stop_reason = from_chat_response(data)
        return LLMResult(
            content=content,
            stop_reason=stop_reason,
            model=data.get("model") or self.model,
            usage=data.get("usage") or {},
        )

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            try:
                resp = await self._http.post("/chat/completions", json=body)
            except httpx.TimeoutException:
                raise LLMError("The assistant took too long to respond. Please try again.", retryable=True)
            except httpx.HTTPError:
                raise LLMError(
                    f"Couldn't reach FreeLLMAPI at {self.base_url}. Please ensure the FreeLLMAPI service is running.",
                    retryable=True,
                )
            try:
                data = resp.json()
            except ValueError:
                data = {}
            error = data.get("error") if isinstance(data, dict) else None
            status = resp.status_code if not (resp.is_success and error) else int((error or {}).get("code") or 502)
            if resp.is_success and not error and isinstance(data, dict) and data.get("choices"):
                return data
            if status in (429, 502, 503) and attempt == 0:
                wait = _retry_after(resp)
                if wait is not None and wait <= MAX_RETRY_WAIT_SECONDS:
                    await asyncio.sleep(wait)
                    continue
            logger.warning("FreeLLMAPI API error", extra={"status": status})
            if status == 401:
                raise LLMError("The assistant is misconfigured (the FreeLLMAPI API key was rejected).")
            if status == 429:
                raise LLMError(
                    "The assistant has reached its usage limit for now. Please try again in a minute.",
                    retryable=True,
                    rate_limited=True,
                )
            if status == 404:
                raise LLMError(
                    f"The assistant is misconfigured (endpoint or model not found at {self.base_url}). Check FREELLMAPI_BASE_URL and FREELLMAPI_MODEL."
                )
            if status in (400, 413, 422):
                msg = (error.get("message") if isinstance(error, dict) else "") or "The assistant couldn't process that request."
                raise LLMError(f"FreeLLMAPI request error: {msg}")
            raise LLMError("The assistant is busy or unavailable right now. Please try again in a minute.", retryable=True)
        raise LLMError("The assistant is busy right now. Please try again in a minute.", retryable=True)

    async def aclose(self) -> None:
        await self._http.aclose()


def _retry_after(resp: httpx.Response) -> float | None:
    try:
        return float(resp.headers.get("retry-after", ""))
    except ValueError:
        return None
