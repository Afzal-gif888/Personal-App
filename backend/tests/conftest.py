"""Test setup. Runs on a temporary SQLite database by default; set TEST_DATABASE_URL to run against
PostgreSQL with pgvector (vector-search tests only run there), e.g. the docker-compose database:

    TEST_DATABASE_URL=postgresql://agentos:agentos@127.0.0.1:5433/agentos_test pytest
"""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="agentos-tests-"))
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = ""
os.environ["AGENT_CORE_MODE"] = "local"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["STORAGE_PATH"] = str(_TMP / "storage")
# Fake EmailJS credentials; the HTTP call itself is replaced by the `emailjs` fixture below.
os.environ.update({"EMAILJS_SERVICE_ID": "service_test", "EMAILJS_TEMPLATE_ID": "template_otp",
                   "EMAILJS_NOTIFICATION_TEMPLATE_ID": "template_notify", "EMAILJS_PUBLIC_KEY": "public-test",
                   "EMAILJS_PRIVATE_KEY": "private-test"})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "CorrectHorse1!"


IS_POSTGRES = engine.dialect.name == "postgresql"
requires_pgvector = pytest.mark.skipif(not IS_POSTGRES, reason="vector search needs PostgreSQL + pgvector (TEST_DATABASE_URL)")


@pytest.fixture(scope="session", autouse=True)
def _schema():
    if IS_POSTGRES:
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class FakeEmailJS:
    """Stands in for the EmailJS REST API and records every request body."""

    def __init__(self):
        self.sent: list[dict] = []
        self.status = 200

    def __call__(self, body):
        import httpx

        self.sent.append(body)
        return httpx.Response(self.status, text="OK" if self.status == 200 else "Bad request")

    def otps(self, email: str) -> list[str]:
        return [b["template_params"]["otp"] for b in self.sent
                if b["template_id"] == "template_otp" and b["template_params"]["to_email"] == email.lower()]

    def notifications(self) -> list[dict]:
        return [b["template_params"] for b in self.sent if b["template_id"] == "template_notify"]


EMAILJS = FakeEmailJS()


@pytest.fixture(autouse=True)
def emailjs(monkeypatch) -> FakeEmailJS:
    EMAILJS.sent.clear()
    EMAILJS.status = 200
    monkeypatch.setattr("app.notifications.emailjs._post", EMAILJS)
    return EMAILJS


def sign_in(client: TestClient, email: str, password: str = PASSWORD) -> dict:
    """Password step, then the emailed code. Returns the session tokens."""
    step1 = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert step1.status_code == 200 and step1.json()["requiresOtp"] is True, step1.text
    resp = client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": EMAILJS.otps(email)[-1]})
    assert resp.status_code == 200, resp.text
    return resp.json()


def register(client: TestClient, email: str = "student@example.com", timezone: str = "Asia/Kolkata") -> dict:
    """Register and sign in (password + emailed code). Returns the session tokens."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"name": "Test Student", "email": email, "password": PASSWORD, "timezone": timezone},
    )
    assert resp.status_code == 201, resp.text
    return sign_in(client, email)


@pytest.fixture
def auth(client) -> dict:
    """Authorization headers for a freshly registered user."""
    return {"Authorization": f"Bearer {register(client)['accessToken']}"}


@pytest.fixture
def other_auth(client) -> dict:
    return {"Authorization": f"Bearer {register(client, 'someone.else@example.com')['accessToken']}"}


@pytest.fixture(autouse=True)
def embeddings(monkeypatch):
    """Document indexing/search use a test-only fake embedder (never the Gemini API) in tests."""
    from tests.fake_embeddings import FakeEmbeddingProvider

    provider = FakeEmbeddingProvider()
    monkeypatch.setattr("app.rag.indexing.get_embedding_provider", lambda: provider)
    monkeypatch.setattr(get_settings_for_tests(), "embedding_api_key", "test-key")
    monkeypatch.setattr(get_settings_for_tests(), "embedding_model", "fake-embedding")
    return provider


def get_settings_for_tests():
    from app.core.config import get_settings

    return get_settings()


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch):
    """The app has no mock fallback; tests run the local agent loop against this test double."""
    from app.services import chat as chat_service
    from tests.mock_llm import MockProvider

    monkeypatch.setattr(chat_service, "get_provider", lambda: MockProvider())
