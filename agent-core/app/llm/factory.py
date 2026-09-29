"""Choose the LLM provider from configuration. There is no mock fallback in the application."""

import logging

from app.config.settings import Settings
from app.llm.base import LLMProvider, UnconfiguredLLMProvider

logger = logging.getLogger(__name__)


def _create(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider
    if not settings.llm_api_key.get_secret_value():
        if settings.app_env == "production":
            raise RuntimeError(f"LLM_PROVIDER={provider} requires LLM_API_KEY")
        logger.error("LLM_API_KEY is empty: the assistant will report that it isn't configured",
                     extra={"llm_provider": provider})
        return UnconfiguredLLMProvider(provider)
    if provider == "anthropic":
        from app.llm.provider import AnthropicProvider

        return AnthropicProvider(settings)
    if provider == "openrouter":
        from app.llm.openrouter import OpenRouterProvider

        return OpenRouterProvider(settings)
    from app.llm.gemini import GeminiProvider

    return GeminiProvider(settings)


def create_llm_provider(settings: Settings) -> LLMProvider:
    provider = _create(settings)
    if provider.name != "unconfigured" and (settings.llm_max_requests_per_minute or settings.llm_max_requests_per_day):
        from app.llm.budget import BudgetedProvider, RequestBudget

        return BudgetedProvider(provider, RequestBudget(settings.llm_max_requests_per_minute, settings.llm_max_requests_per_day))
    return provider
