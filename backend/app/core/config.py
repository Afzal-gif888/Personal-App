"""Application settings, loaded from environment variables (and an optional .env file)."""

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEV_SECRET = "dev-only-insecure-secret-change-me"


def _normalise_origin(value: str) -> str:
    """Write an origin the way browsers send it in the Origin header, which CORS compares exactly.

    Values pasted into a hosting dashboard often carry a trailing slash (copied from the address
    bar), quotes or capitals; any of those made the match fail and the preflight lose its
    Access-Control-Allow-Origin header. Scheme and host are case-insensitive, so they're lowered.
    """
    origin = str(value).strip().strip("\"'").strip().rstrip("/")
    if origin == "*" or "://" not in origin:
        return origin
    scheme, rest = origin.split("://", 1)
    return f"{scheme.lower()}://{rest.lower()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "It's Personal API"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://agentos:agentos@localhost:5432/agentos"

    jwt_secret: str = _DEV_SECRET
    jwt_refresh_secret: str = _DEV_SECRET + "-refresh"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 14

    # Only used when AGENT_CORE_MODE=local: "anthropic" plus LLM_API_KEY. Empty = not configured (no mock).
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    llm_timeout_seconds: float = 60.0
    llm_max_tokens: int = 16000
    # Re-run refused requests on a fallback model server-side (claude-opus-5 / claude-fable-5-1 only).
    llm_refusal_fallback: bool = True

    # "local" runs the in-process development agent; "http" calls an external Agent Core service.
    agent_core_mode: Literal["local", "http", "agent"] = "local"
    agent_core_url: str = ""
    agent_core_service_token: str = ""
    agent_core_timeout_seconds: float = 120.0
    approval_ttl_hours: int = 72
    agent_max_iterations: int = 8
    agent_history_messages: int = 20

    storage_provider: Literal["local"] = "local"
    storage_path: str = "./storage"
    max_upload_mb: int = 25

    # NoDecode: read the raw string so plain comma-separated values work, not only JSON.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])
    # Optional: also allow origins matching this regex, e.g. every Vercel deployment URL of one
    # project, which changes on each deploy: ^https://its-personal-[a-z0-9]+-xdark1\.vercel\.app$
    cors_origin_regex: str = ""

    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 20
    rate_limit_chat_per_minute: int = 30

    scheduler_enabled: bool = False
    scheduler_interval_seconds: int = 60

    # Email through EmailJS (server-side REST API). Login OTPs need these; without them nobody can sign in.
    emailjs_service_id: str = ""
    emailjs_template_id: str = ""  # login OTP template: {{name}}, {{otp}}
    emailjs_notification_template_id: str = ""  # reminders + password reset: {{name}}, {{subject}}, {{message}}
    emailjs_public_key: str = ""
    emailjs_private_key: str = ""
    emailjs_timeout_seconds: float = 15.0
    app_base_url: str = "http://localhost:5173"  # links in emails

    # Document search (RAG): Gemini embeddings stored in PostgreSQL + pgvector. Documents are
    # embedded once when uploaded; a search embeds only the query.
    embedding_provider: Literal["", "gemini"] = "gemini"  # "" turns document search off
    embedding_api_key: str = ""  # a Gemini API key (never sent to the frontend)
    embedding_model: str = ""  # e.g. gemini-embedding-2; required when the provider is set
    # Must equal the document_chunks.embedding column size (a migration changes it).
    embedding_dimensions: int = 768
    embedding_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    embedding_timeout_seconds: float = 60.0
    document_search_top_k: int = Field(default=5, ge=1, le=20)
    # Cosine similarity below this is "not relevant". Calibrated on a real PDF with gemini-embedding-2:
    # matching passages scored 0.68-0.75, unrelated questions at most 0.62.
    document_search_min_similarity: float = Field(default=0.65, ge=0, le=1)
    # Smaller chunks give sharper matches than long mixed-topic ones (measured: 0.72 vs 0.67).
    document_chunk_chars: int = Field(default=600, ge=200, le=8000)
    document_chunk_overlap: int = Field(default=100, ge=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            value = json.loads(value) if value.startswith("[") else value.split(",")
        return [o for o in (_normalise_origin(v) for v in value) if o]

    @field_validator("database_url")
    @classmethod
    def _normalise_driver(cls, value: str) -> str:
        # Accept plain postgres:// URLs (as most hosts hand out) and pin the psycopg 3 driver.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @model_validator(mode="after")
    def _check_production(self):
        # A blank JWT_SECRET= line (as in .env.example) means "not set", not an empty signing key.
        if not self.jwt_secret.strip():
            self.jwt_secret = _DEV_SECRET
        if not self.jwt_refresh_secret.strip():
            self.jwt_refresh_secret = _DEV_SECRET + "-refresh"
        if self.app_env == "production":
            if self.jwt_secret.startswith(_DEV_SECRET) or self.jwt_refresh_secret.startswith(_DEV_SECRET):
                raise ValueError("JWT_SECRET and JWT_REFRESH_SECRET must be set in production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS_ORIGINS is not allowed in production")
            if self.cors_origin_regex and not (self.cors_origin_regex.startswith("^https://")
                                               and self.cors_origin_regex.endswith("$")):
                raise ValueError("CORS_ORIGIN_REGEX must be anchored: ^https://...$ in production")
            # A missing DATABASE_URL would otherwise fall back to the localhost default and fail
            # later with a confusing connection error.
            if self.is_sqlite or any(h in self.database_url for h in ("@localhost", "@127.0.0.1")):
                raise ValueError("DATABASE_URL must point at the production database (e.g. Neon) in production")
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @field_validator("llm_provider")
    @classmethod
    def _check_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in ("", "anthropic"):
            raise ValueError("LLM_PROVIDER must be empty or 'anthropic'")
        return value

    @property
    def embeddings_configured(self) -> bool:
        return bool(self.embedding_provider and self.embedding_api_key and self.embedding_model)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_provider and self.llm_api_key)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
