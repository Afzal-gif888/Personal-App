"""Comprehensive unit tests for FreeLLMAPIClient, Mock Server, and Healthcheck CLI."""

import asyncio
import json
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.llm.freellmapi import FreeLLMAPIClient, FreeLLMAPIError, _RETRYABLE_STATUS
from app.llm.healthcheck import check, mask_key, scrub_url
from mock_freellmapi import app as mock_app, VALID_KEY


@pytest.fixture
def mock_transport():
    """Hermetic ASGI transport directly connected to mock_freellmapi app."""
    return httpx.ASGITransport(app=mock_app)


@pytest.fixture
def client(mock_transport):
    """Client pointing to mock app with valid key and test transport."""
    return FreeLLMAPIClient(
        base_url="http://mock-freellmapi/v1",
        api_key=VALID_KEY,
        default_model="auto",
        timeout=10.0,
        transport=mock_transport,
    )


def test_error_attributes():
    err = FreeLLMAPIError("HTTP_404", "Model not found", 404)
    assert err.code == "HTTP_404"
    assert err.status_code == 404
    assert "Model not found" in str(err)


def test_missing_api_key_raises():
    c = FreeLLMAPIClient(base_url="http://mock-freellmapi/v1", api_key=None)
    with pytest.raises(FreeLLMAPIError) as exc_info:
        c._headers()
    assert exc_info.value.code == "NOT_CONFIGURED"
    assert exc_info.value.status_code == 503
    assert "FREELLMAPI_API_KEY is missing" in str(exc_info.value)


def test_headers_with_request_id():
    c = FreeLLMAPIClient(base_url="http://mock-freellmapi/v1", api_key="my-key")
    headers = c._headers(request_id="req-12345")
    assert headers["Authorization"] == "Bearer my-key"
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Request-ID"] == "req-12345"


@pytest.mark.asyncio
async def test_chat_completion_success(client):
    messages = [{"role": "user", "content": "Hello!"}]
    reply = await client.chat_completion(messages, request_id="corr-test")
    assert reply == "This is a verified mock response from FreeLLMAPI."
    await client.aclose()


@pytest.mark.asyncio
async def test_stream_chat_completion_success(client):
    messages = [{"role": "user", "content": "Stream test"}]
    chunks = []
    async for chunk in client.stream_chat_completion(messages, request_id="corr-stream"):
        chunks.append(chunk)

    full_text = "".join(chunks).strip()
    assert full_text == "This is a verified mock response from FreeLLMAPI."
    await client.aclose()


@pytest.mark.asyncio
async def test_fail_fast_on_invalid_api_key(mock_transport):
    bad_client = FreeLLMAPIClient(
        base_url="http://mock-freellmapi/v1",
        api_key="wrong-key",
        transport=mock_transport,
    )
    with pytest.raises(FreeLLMAPIError) as exc_info:
        await bad_client.chat_completion([{"role": "user", "content": "Hi"}])

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "HTTP_401"
    await bad_client.aclose()


@pytest.mark.asyncio
async def test_stream_fail_fast_on_invalid_api_key(mock_transport):
    bad_client = FreeLLMAPIClient(
        base_url="http://mock-freellmapi/v1",
        api_key="wrong-key",
        transport=mock_transport,
    )
    with pytest.raises(FreeLLMAPIError) as exc_info:
        async for _ in bad_client.stream_chat_completion([{"role": "user", "content": "Hi"}]):
            pass

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "HTTP_401"
    await bad_client.aclose()


@pytest.mark.asyncio
async def test_retry_on_500_and_succeed():
    attempt_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return httpx.Response(500, json={"error": "internal gateway error"})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "Recovered after 500."}}
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    c = FreeLLMAPIClient(
        base_url="http://mock-gateway/v1",
        api_key="test-key",
        max_retries=2,
        transport=transport,
    )
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        res = await c.chat_completion([{"role": "user", "content": "ping"}])
        assert res == "Recovered after 500."
        assert attempt_count == 2
        assert mock_sleep.await_count == 1
    await c.aclose()


@pytest.mark.asyncio
async def test_retry_on_429_with_retry_after():
    attempt_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return httpx.Response(
                429,
                headers={"retry-after": "2"},
                json={"error": "rate limited"},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "Recovered after 429."}}
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    c = FreeLLMAPIClient(
        base_url="http://mock-gateway/v1",
        api_key="test-key",
        max_retries=2,
        transport=transport,
    )
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        res = await c.chat_completion([{"role": "user", "content": "ping"}])
        assert res == "Recovered after 429."
        assert attempt_count == 2
        # sleep should be based on retry-after (~2.0s + jitter)
        sleep_arg = mock_sleep.call_args[0][0]
        assert 2.0 <= sleep_arg <= 2.5
    await c.aclose()


@pytest.mark.asyncio
async def test_retry_exhaustion_on_persistent_503():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "service unavailable"})

    transport = httpx.MockTransport(mock_handler)
    c = FreeLLMAPIClient(
        base_url="http://mock-gateway/v1",
        api_key="test-key",
        max_retries=2,
        transport=transport,
    )
    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(FreeLLMAPIError) as exc_info:
            await c.chat_completion([{"role": "user", "content": "ping"}])
        assert exc_info.value.status_code == 503
        assert exc_info.value.code == "HTTP_503"
    await c.aclose()


@pytest.mark.asyncio
async def test_timeout_raises_freellmapierror():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    transport = httpx.MockTransport(mock_handler)
    c = FreeLLMAPIClient(
        base_url="http://mock-gateway/v1",
        api_key="test-key",
        max_retries=1,
        transport=transport,
    )
    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(FreeLLMAPIError) as exc_info:
            await c.chat_completion([{"role": "user", "content": "ping"}])
        assert exc_info.value.code == "TIMEOUT"
        assert exc_info.value.status_code == 504
    await c.aclose()


def test_scrub_url_removes_credentials():
    dirty_url = "http://user:secretpassword123@gateway.internal:31415/v1"
    clean_url = scrub_url(dirty_url)
    assert "secretpassword123" not in clean_url
    assert "user" not in clean_url
    assert clean_url == "http://gateway.internal:31415/v1"

    plain_url = "http://127.0.0.1:31415/v1"
    assert scrub_url(plain_url) == plain_url


def test_mask_key():
    assert mask_key("freellmapi-secret-abc-123") == "Configured"
    assert mask_key("") == "MISSING"
    assert mask_key(None) == "MISSING"


@pytest.mark.asyncio
async def test_healthcheck_cli_success(mock_transport, monkeypatch):
    monkeypatch.setenv("FREELLMAPI_BASE_URL", "http://mock-freellmapi/v1")
    monkeypatch.setenv("FREELLMAPI_API_KEY", VALID_KEY)
    monkeypatch.setenv("FREELLMAPI_MODEL", "auto")

    exit_code = await check(chat=True, transport=mock_transport)
    assert exit_code == 0


@pytest.mark.asyncio
async def test_healthcheck_cli_missing_key(monkeypatch):
    monkeypatch.delenv("FREELLMAPI_API_KEY", raising=False)
    exit_code = await check(chat=False)
    assert exit_code == 1


@pytest.mark.asyncio
async def test_healthcheck_cli_bad_auth(mock_transport, monkeypatch):
    monkeypatch.setenv("FREELLMAPI_BASE_URL", "http://mock-freellmapi/v1")
    monkeypatch.setenv("FREELLMAPI_API_KEY", "invalid-key")
    exit_code = await check(chat=False, transport=mock_transport)
    assert exit_code == 1


@pytest.mark.asyncio
async def test_mock_server_direct_models(mock_transport):
    async with httpx.AsyncClient(transport=mock_transport, base_url="http://mock-server") as client:
        # Valid auth
        res = await client.get("/v1/models", headers={"Authorization": f"Bearer {VALID_KEY}"})
        assert res.status_code == 200
        data = res.json()
        ids = [m["id"] for m in data["data"]]
        assert "auto" in ids
        assert "auto:fast" in ids
        assert "llama-3.3-70b" in ids

        # Missing auth
        res_no_auth = await client.get("/v1/models")
        assert res_no_auth.status_code == 401
