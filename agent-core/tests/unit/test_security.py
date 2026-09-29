import logging

from app.security import RedactingFilter, redact, tokens_match


def test_redact_nested_secrets():
    data = {"password": "hunter2", "nested": {"api_key": "k", "note": "Bearer abc.def.ghi"}, "card_number": "4111",
            "items": [{"token": "t"}], "title": "fine"}
    out = redact(data)
    assert out["password"] == out["nested"]["api_key"] == out["card_number"] == out["items"][0]["token"] == "[REDACTED]"
    assert out["nested"]["note"] == "Bearer [REDACTED]" and out["title"] == "fine"


def test_logging_filter_scrubs_keys_and_tokens():
    record = logging.LogRecord("x", logging.INFO, "", 0, "auth Bearer sk-ant-abcdefghijklmnop", (), None)
    # What logger.info(..., extra={...}) does to a record.
    record.__dict__.update(authorization="Bearer secret", payload={"llm_api_key": "sk-ant-zzzzzzzzzzzzzzzz"})
    RedactingFilter().filter(record)
    assert "sk-ant" not in record.getMessage() and record.__dict__["authorization"] == "[REDACTED]"
    assert record.__dict__["payload"] == {"llm_api_key": "[REDACTED]"}


def test_token_compare():
    assert tokens_match("abc", "abc") and not tokens_match("abc", "abd") and not tokens_match("", "")
