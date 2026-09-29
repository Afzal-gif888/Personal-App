"""Delegate model calls to an external Agent Core service (AGENT_CORE_MODE=http).

The Agent Core only decides what to say and which tools to call. Tools still execute here, against
this API's database and its approval rules, so a remote core can never write without approval.

Contract: POST {AGENT_CORE_URL}/v1/complete with bearer AGENT_CORE_SERVICE_TOKEN and body
    {"system": str, "messages": [...], "tools": [{"name", "description", "input_schema"}]}
responding with
    {"content": [<Messages API content blocks>], "stop_reason": str, "model": str?}
"""

from typing import Any

import httpx

from app.core.config import Settings
from app.llm import LLMError, LLMResponse, ToolSpec


class AgentCoreProvider:
    name = "agent_core"

    def __init__(self, settings: Settings) -> None:
        if not settings.agent_core_url:
            raise RuntimeError("AGENT_CORE_URL is required when AGENT_CORE_MODE=http")
        self.url = settings.agent_core_url.rstrip("/") + "/v1/complete"
        self.headers = {"Authorization": f"Bearer {settings.agent_core_service_token}"}
        self.timeout = settings.agent_core_timeout_seconds

    def complete(self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> LLMResponse:
        body = {
            "system": system,
            "messages": messages,
            "tools": [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools],
        }
        try:
            resp = httpx.post(self.url, json=body, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"]
            if not isinstance(content, list):
                raise ValueError("content must be a list")
        except httpx.HTTPStatusError as exc:
            raise LLMError("The assistant service returned an error.", retryable=exc.response.status_code >= 500)
        except httpx.HTTPError:
            raise LLMError("Couldn't reach the assistant service. Please try again.", retryable=True)
        except (ValueError, KeyError, TypeError):
            raise LLMError("The assistant service sent an invalid response.")
        return LLMResponse(content=content, stop_reason=data.get("stop_reason", "end_turn"), model=data.get("model", ""))
