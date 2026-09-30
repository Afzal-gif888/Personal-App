import os
from datetime import date

import pytest

# Tests never read the developer's .env and never need a real API key.
os.environ.setdefault("APP_ENV", "test")
for key in ("LLM_PROVIDER", "LLM_API_KEY", "AGENT_CORE_SERVICE_TOKEN"):
    os.environ.pop(key, None)

from app.agent.graph import AgentRunner  # noqa: E402
from app.agent.nodes import RunDeps  # noqa: E402
from app.backend.client import BackendClient  # noqa: E402
from app.config.settings import Settings  # noqa: E402
from app.main import build_services  # noqa: E402
from app.schemas.agent import AgentRunRequest, UserContext  # noqa: E402
from app.tools.registry import ToolContext  # noqa: E402
from tests.fakes import TOKEN_A, USER_A, FakeBackend  # noqa: E402
from tests.mock_llm import MockLLMProvider  # noqa: E402

SERVICE_TOKEN = "test-service-token-123"


def make_settings(**overrides) -> Settings:
    base = {"app_env": "test", "backend_api_url": "http://backend.test", "llm_provider": "gemini", "_env_file": None}
    return Settings(**{**base, **overrides})


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def backend() -> FakeBackend:
    fake = FakeBackend(today=date.today())
    fake.seed_student()
    return fake


class Harness:
    """Runs the real graph against the fake backend with a chosen LLM."""

    def __init__(self, backend: FakeBackend, settings: Settings, llm=None) -> None:
        self.fake = backend
        self.settings = settings
        self.services = build_services(settings, llm=llm or MockLLMProvider(), backend_transport=backend.transport())
        self.runner = AgentRunner()

    def client(self, token: str = TOKEN_A) -> BackendClient:
        return BackendClient(self.settings.backend_api_url, token, transport=self.fake.transport())

    async def run(self, message: str, *, token: str = TOKEN_A, **request):
        svc = self.services
        async with self.client(token) as backend:
            deps = RunDeps(settings=svc.settings, llm=svc.llm, registry=svc.registry, approvals=svc.approvals,
                           memory=svc.memory, backend=backend)
            return await self.runner.run(AgentRunRequest(message=message, **request), deps)


@pytest.fixture
def harness(backend, settings) -> Harness:
    return Harness(backend, settings)


@pytest.fixture
def tool_ctx(backend, settings):
    """A ToolContext for calling tools directly, bound to user A."""
    h = Harness(backend, settings)
    client = h.client()
    user = UserContext(user_id=USER_A, name="Asha", timezone="Asia/Kolkata",
                       preferences={"default_reminder_time": "09:00"})
    ctx = ToolContext(backend=client, user=user, today=backend.today, memory=h.services.memory.long_term)
    return h, ctx
