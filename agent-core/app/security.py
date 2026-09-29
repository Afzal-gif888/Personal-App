"""Secret handling helpers shared by logging and tool-call records."""

import hmac
import logging
import re
from typing import Any

SENSITIVE_KEYS = re.compile(
    r"pass(word)?|secret|token|api[_-]?key|authorization|cookie|credential|private[_-]?key|"
    r"card|cvv|cvc|iban|account[_-]?number|routing|pin\b",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.=]+", re.IGNORECASE)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")
_KEY = re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_\-]{12,}")


def redact_text(value: str) -> str:
    value = _BEARER.sub(r"\1[REDACTED]", value)
    value = _JWT.sub("[REDACTED_JWT]", value)
    return _KEY.sub("[REDACTED_KEY]", value)


def redact(value: Any) -> Any:
    """Recursively strip secrets from dicts/lists before they are logged or returned as metadata."""
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if isinstance(k, str) and SENSITIVE_KEYS.search(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def tokens_match(presented: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(presented.encode(), expected.encode())


class RedactingFilter(logging.Filter):
    """Last line of defence: scrub bearer tokens, JWTs and API keys from every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            record.args = tuple(redact(a) for a in record.args) if isinstance(record.args, tuple) else redact(record.args)
        for key, value in list(record.__dict__.items()):
            if SENSITIVE_KEYS.search(key):
                record.__dict__[key] = "[REDACTED]"
            elif key == "extra" or isinstance(value, dict):
                record.__dict__[key] = redact(value)
        return True
