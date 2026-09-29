"""Structured JSON logging with request IDs and secret redaction."""

import contextvars
import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

SENSITIVE_KEYS = re.compile(
    r"pass(word)?|secret|token|api[_-]?key|authorization|cookie|credential|private[_-]?key", re.IGNORECASE
)
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.=]+", re.IGNORECASE)
_JWT = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
_SK = re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_\-]{12,}")
# One-time tokens in URLs (e.g. a password-reset link's ?token=...) must never reach access logs.
_QUERY_TOKEN = re.compile(r"([?&](?:token|code)=)[^&\s\"']+", re.IGNORECASE)


def redact_text(value: str) -> str:
    value = _QUERY_TOKEN.sub(r"\1[REDACTED]", value)
    value = _BEARER.sub(r"\1[REDACTED]", value)
    value = _JWT.sub("[REDACTED_JWT]", value)
    return _SK.sub("[REDACTED_KEY]", value)


def redact(value: Any) -> Any:
    """Recursively strip secrets from dicts/lists before they are logged or persisted."""
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if isinstance(k, str) and SENSITIVE_KEYS.search(k) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class JsonFormatter(logging.Formatter):
    _RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        if rid := request_id_var.get():
            entry["request_id"] = rid
        extra = {k: v for k, v in record.__dict__.items() if k not in self._RESERVED}
        if extra:
            entry.update(redact(extra))
        if record.exc_info:
            entry["exc_info"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # These loggers format their own lines (request URLs included), so scrub secrets at the source.
    for name in ("uvicorn.access", "uvicorn.error", "httpx", "httpx2"):
        target = logging.getLogger(name)
        if not any(isinstance(f, RedactingFilter) for f in target.filters):
            target.addFilter(RedactingFilter())


class RedactingFilter(logging.Filter):
    """Redact tokens in a record's message and its %-format arguments (e.g. uvicorn's request line)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact_text(str(a)) if "token=" in str(a) or isinstance(a, str) else a for a in record.args)
        return True
