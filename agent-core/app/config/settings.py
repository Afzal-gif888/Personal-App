"""Agent Core configuration. Every value comes from the environment (or `.env`); nothing secret is hardcoded."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "It's Personal Agent Core"
    log_level: str = "INFO"
    agent_core_port: int = 8001

    # Service-to-service auth: the backend sends `Authorization: Bearer <token>` on every call.
    # Required in production; in development an empty token disables the check.
    agent_core_service_token: SecretStr = SecretStr("")

    # LLM: "openrouter" = OpenRouter (free ':free' models available); "gemini" = Google Gemini (AI Studio key);
    # "anthropic" = Claude (paid API). There is no mock: without LLM_API_KEY the assistant says it isn't set up.
    llm_provider: Literal["openrouter", "gemini", "anthropic"] = "gemini"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    llm_base_url: str = ""
    llm_max_tokens: int = Field(default=16000, ge=256, le=128000)
    llm_timeout_seconds: float = Field(default=90.0, gt=0)
    llm_refusal_fallback: bool = True
    # Gemini / OpenRouter: comma-separated models to try when LLM_MODEL is overloaded or out of quota.
    # Empty = the provider's built-in free-model chain.
    llm_fallback_models: str = ""
    # One extra LLM call per multi-step request to draft a plan. Turn off to save free-tier quota.
    llm_planning: bool = True
    # Request budget for model calls (0 = unlimited). Keep below the provider's free-tier limits.
    llm_max_requests_per_minute: int = Field(default=0, ge=0)
    llm_max_requests_per_day: int = Field(default=0, ge=0)

    # The FastAPI backend (base URL without /api/v1).
    backend_api_url: str = "http://localhost:8000"
    backend_timeout_seconds: float = Field(default=15.0, gt=0)

    # Loop safety.
    max_agent_iterations: int = Field(default=10, ge=1, le=50)
    max_tool_calls: int = Field(default=20, ge=1, le=200)
    agent_timeout_seconds: float = Field(default=120.0, gt=0)
    tool_timeout_seconds: float = Field(default=20.0, gt=0)
    max_request_chars: int = Field(default=8000, ge=100)
    history_messages: int = Field(default=12, ge=0, le=100)

    # Approvals. "direct" runs create/update tools immediately; "approval" queues them too.
    # Consequential tools (deletes, external side effects) always require approval.
    mutation_policy: Literal["direct", "approval"] = "direct"
    approval_ttl_seconds: int = Field(default=72 * 3600, ge=60)

    # Document search is done by the backend (Gemini embeddings + pgvector); nothing to set here.

    @field_validator("backend_api_url")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.app_env == "production" and not self.agent_core_service_token.get_secret_value():
            raise ValueError("AGENT_CORE_SERVICE_TOKEN is required in production")
        return self

    @property
    def llm_is_real(self) -> bool:
        return bool(self.llm_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
