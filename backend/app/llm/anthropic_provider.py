import logging
from typing import Any

import anthropic

from app.core.config import Settings
from app.llm import LLMError, LLMResponse, ToolSpec

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"
# Models whose safety classifiers can decline a request; for these, a declined request is re-run
# server-side on Anthropic's recommended fallback model instead of coming back as a refusal.
FALLBACK_MODELS = {"claude-opus-5", "claude-opus-5-5", "claude-fable-5-1"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        self.client = anthropic.Anthropic(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
        )
        self.model = settings.llm_model or DEFAULT_MODEL
        self.max_tokens = settings.llm_max_tokens
        self.use_fallback = settings.llm_refusal_fallback and self.model in FALLBACK_MODELS

    def complete(self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]) -> LLMResponse:
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
            "tools": [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools],
        }
        try:
            if self.use_fallback:
                response = self.client.beta.messages.create(**params, betas=[FALLBACK_BETA], fallbacks="default")
            else:
                response = self.client.messages.create(**params)
        except anthropic.AuthenticationError as exc:
            logger.error("LLM authentication failed", extra={"status": exc.status_code})
            raise LLMError("The assistant is misconfigured. Please contact the administrator.")
        except anthropic.RateLimitError:
            raise LLMError("The assistant is busy right now. Please try again in a minute.", retryable=True)
        except anthropic.BadRequestError as exc:
            logger.error("LLM rejected the request", extra={"error": exc.message})
            raise LLMError("The assistant couldn't process that request.")
        except anthropic.APIStatusError as exc:
            logger.warning("LLM API error", extra={"status": exc.status_code, "error": exc.message})
            raise LLMError("The assistant is temporarily unavailable. Please try again.", retryable=exc.status_code >= 500)
        except anthropic.APIConnectionError:
            raise LLMError("Couldn't reach the assistant service. Please try again.", retryable=True)

        return LLMResponse(
            content=[block.to_dict() for block in response.content],
            stop_reason=response.stop_reason or "end_turn",
            model=response.model,
            usage=response.usage.to_dict() if response.usage else {},
        )
