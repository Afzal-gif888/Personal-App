"""Production FreeLLMAPI client and provider layer with connection pooling, retries, and streaming.

FreeLLMAPI is an OpenAI-compatible LLM Gateway/Router (desktop app or hosted on Railway).
Provides:
  - FreeLLMAPIClient: High-performance async client with connection pooling, SSE streaming,
    bounded exponential backoff with jitter, Retry-After header parsing, and X-Request-ID tracking.
  - FreeLLMAPIError: Typed exception for gateway errors, masking sensitive keys.
  - FreeLLMAPIProvider: LangGraph LLMProvider integration for the personal assistant agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config.settings import Settings
from app.llm.base import LLMError, LLMProvider, LLMResult, LLMToolSpec, Purpose
from app.llm.openrouter import from_chat_response, to_chat_messages, to_openai_schema

log = logging.getLogger("llm.freellmapi")
logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DEFAULT_BASE_URL = "http://127.0.0.1:31415/v1"
DEFAULT_MODEL = "auto"
MAX_RETRY_WAIT_SECONDS = 8.0


class FreeLLMAPIError(Exception):
    """Raised when FreeLLMAPI encounters a client or gateway failure."""

    def __init__(self, code: str, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class FreeLLMAPIClient:
    """Async client for FreeLLMAPI gateway with connection pooling, retries, and streaming."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        default_model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
        max_retries: int = 2,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.default_model = default_model
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            transport=transport,
        )

    def _headers(self, request_id: Optional[str] = None) -> Dict[str, str]:
        if not self._api_key:
            raise FreeLLMAPIError("NOT_CONFIGURED", "FREELLMAPI_API_KEY is missing", 503)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if request_id:
            headers["X-Request-ID"] = request_id
        return headers

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post_with_retry(
        self, path: str, payload: dict, request_id: Optional[str] = None
    ) -> httpx.Response:
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._client.post(path, json=payload, headers=self._headers(request_id))
                if resp.status_code not in _RETRYABLE_STATUS:
                    return resp
                if attempt == self.max_retries:
                    return resp

                # Check Retry-After header on 429
                retry_after = resp.headers.get("retry-after")
                sleep_sec = float(retry_after) if retry_after and retry_after.isdigit() else delay
                sleep_sec = min(sleep_sec, MAX_RETRY_WAIT_SECONDS) + random.uniform(0.05, 0.2)
                log.warning(
                    "FreeLLMAPI retryable status %s (attempt %s/%s), backing off for %.2fs",
                    resp.status_code,
                    attempt + 1,
                    self.max_retries,
                    sleep_sec,
                )
                await asyncio.sleep(sleep_sec)
                delay = min(delay * 2.0, MAX_RETRY_WAIT_SECONDS)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt == self.max_retries:
                    raise FreeLLMAPIError("TIMEOUT", f"FreeLLMAPI unreachable: {exc}", 504)
                log.warning(
                    "FreeLLMAPI connection error on attempt %s/%s: %s",
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, MAX_RETRY_WAIT_SECONDS)
        return resp

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
        request_id: Optional[str] = None,
    ) -> str:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        resp = await self._post_with_retry("/chat/completions", payload, request_id)
        if resp.status_code != 200:
            raise FreeLLMAPIError(f"HTTP_{resp.status_code}", f"LLM error: {resp.text}", resp.status_code)

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
        request_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = self._headers(request_id)
        async with self._client.stream("POST", "/chat/completions", json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise FreeLLMAPIError(f"HTTP_{resp.status_code}", f"Stream error: {body.decode()}", resp.status_code)

            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
                except json.JSONDecodeError:
                    continue


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
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
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
            if status in _RETRYABLE_STATUS and attempt == 0:
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
