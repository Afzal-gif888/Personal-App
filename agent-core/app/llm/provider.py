"""Anthropic (Claude) provider, via the official SDK."""

import logging
from typing import Any

import anthropic

from app.config.settings import Settings
from app.llm.base import LLMError, LLMProvider, LLMResult, LLMToolSpec, Purpose

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"
# Models whose safety classifiers can decline a request. For these, a declined request is re-run
# server-side on Anthropic's recommended fallback model instead of returning a refusal.
FALLBACK_MODELS = {"claude-opus-5", "claude-opus-5-5", "claude-fable-5-1"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
_PRE_FALLBACK_DROP = {"thinking", "redacted_thinking", "tool_use", "server_tool_use"}


def sanitize_fallback_content(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """After a mid-output fallback, blocks before the last `fallback` marker other than text must not
    be echoed back (or executed). The marker itself is an audit block and is dropped."""
    last = max((i for i, b in enumerate(blocks) if b.get("type") == "fallback"), default=-1)
    if last < 0:
        return blocks
    kept = [b for b in blocks[:last] if b.get("type") not in _PRE_FALLBACK_DROP and b.get("type") != "fallback"]
    return kept + [b for b in blocks[last + 1 :] if b.get("type") != "fallback"]


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.llm_api_key.get_secret_value(),
            base_url=settings.llm_base_url or None,
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
        )
        self.model = settings.llm_model or DEFAULT_MODEL
        self.max_tokens = settings.llm_max_tokens
        self.use_fallback = settings.llm_refusal_fallback and self.model in FALLBACK_MODELS

    async def invoke(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[LLMToolSpec], purpose: Purpose = "act"
    ) -> LLMResult:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
            "thinking": {"type": "adaptive"},
        }
        if purpose == "plan":
            params["output_config"] = {"effort": "low"}  # a short plan does not need deep reasoning
        if tools:
            params["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]
            params["cache_control"] = {"type": "ephemeral"}  # tool definitions + system are a stable prefix
        try:
            if self.use_fallback:
                response = await self.client.beta.messages.create(**params, betas=[FALLBACK_BETA], fallbacks="default")
            else:
                response = await self.client.messages.create(**params)
        except anthropic.AuthenticationError as exc:
            logger.error("LLM authentication failed", extra={"status": exc.status_code})
            raise LLMError("The assistant is misconfigured. Please contact the administrator.")
        except anthropic.RateLimitError:
            raise LLMError("The assistant is busy right now. Please try again in a minute.", retryable=True, rate_limited=True)
        except anthropic.BadRequestError as exc:
            logger.error("LLM rejected the request", extra={"status": exc.status_code})
            raise LLMError("The assistant couldn't process that request.")
        except anthropic.APITimeoutError:
            raise LLMError("The assistant took too long to respond. Please try again.", retryable=True)
        except anthropic.APIStatusError as exc:
            logger.warning("LLM API error", extra={"status": exc.status_code})
            raise LLMError("The assistant is temporarily unavailable. Please try again.", retryable=exc.status_code >= 500)
        except anthropic.APIConnectionError:
            raise LLMError("Couldn't reach the assistant service. Please try again.", retryable=True)

        content = sanitize_fallback_content([block.to_dict() for block in response.content])
        return LLMResult(
            content=content,
            stop_reason=response.stop_reason or "end_turn",
            model=response.model,
            usage=response.usage.to_dict() if response.usage else {},
        )

    async def aclose(self) -> None:
        await self.client.close()
