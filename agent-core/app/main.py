"""Agent Core HTTP service.

Production flow: Frontend -> Backend -> Agent Core -> LLM. The frontend never calls this service.

Every agent endpoint needs two credentials from the backend:
* `Authorization: Bearer <AGENT_CORE_SERVICE_TOKEN>` - proves the caller is the backend.
* `X-User-Authorization: Bearer <user access token>` - the signed-in user's backend token. The
  Agent Core uses it for every backend call, so the backend decides whose data is reachable; a
  `user_id` in the body is only checked against it, never trusted on its own.
"""

import json
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent.graph import AgentRunner
from app.agent.nodes import RunDeps
from app.approvals.manager import (
    ApprovalExpiredError,
    ApprovalManager,
    ApprovalNotFoundError,
    ApprovalStateError,
    InMemoryApprovalStore,
)
from app.backend.client import BackendClient
from app.backend.exceptions import BackendAuthError, BackendError
from app.config.settings import Settings, get_settings
from app.llm.base import LLMError, LLMProvider, LLMToolSpec
from app.llm.factory import create_llm_provider
from app.memory.long_term import LongTermMemory
from app.memory.manager import MemoryManager
from app.memory.short_term import ShortTermMemory
from app.schemas.agent import (
    AgentError,
    AgentRunRequest,
    AgentRunResponse,
    ApprovalDecisionResponse,
    ErrorCode,
    UserContext,
)
from app.security import RedactingFilter, redact_text, tokens_match
from app.tools.registry import (
    ALL_SCOPES,
    ToolContext,
    ToolError,
    ToolInputError,
    ToolRegistry,
    build_default_registry,
)

logger = logging.getLogger("app")


class JsonFormatter(logging.Formatter):
    _RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        entry.update({k: v for k, v in record.__dict__.items() if k not in self._RESERVED})
        if record.exc_info:
            entry["exc_info"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(entry, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # httpx logs full URLs at INFO; keep it quiet so nothing request-specific leaks.
    logging.getLogger("httpx").setLevel(logging.WARNING)


@dataclass
class Services:
    settings: Settings
    llm: LLMProvider
    registry: ToolRegistry
    approvals: ApprovalManager
    memory: MemoryManager
    runner: AgentRunner
    backend_transport: httpx.AsyncBaseTransport | None = None

    def backend(self, user_token: str, request_id: str) -> BackendClient:
        return BackendClient(
            self.settings.backend_api_url, user_token, timeout=self.settings.backend_timeout_seconds,
            request_id=request_id, transport=self.backend_transport,
        )


def build_services(
    settings: Settings, *, llm: LLMProvider | None = None, backend_transport: httpx.AsyncBaseTransport | None = None
) -> Services:
    registry = build_default_registry(settings.tool_timeout_seconds)
    return Services(
        settings=settings,
        llm=llm or create_llm_provider(settings),
        registry=registry,
        approvals=ApprovalManager(InMemoryApprovalStore(), ttl_seconds=settings.approval_ttl_seconds, registry=registry),
        memory=MemoryManager(ShortTermMemory(max_messages=settings.history_messages), LongTermMemory()),
        runner=AgentRunner(),
        backend_transport=backend_transport,
    )


def error_response(status: int, code: ErrorCode | str, message: str, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": str(code), "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(body, status_code=status)


class ApiError(HTTPException):
    def __init__(self, status: int, code: ErrorCode, message: str) -> None:
        super().__init__(status_code=status, detail=message)
        self.code = code


# --- dependencies --------------------------------------------------------------------------------


def services(request: Request) -> Services:
    return request.app.state.services


Svc = Annotated[Services, Depends(services)]


def require_service(svc: Svc, authorization: Annotated[str | None, Header()] = None) -> None:
    expected = svc.settings.agent_core_service_token.get_secret_value()
    if not expected:
        return  # development without a token configured (refused at startup in production)
    presented = (authorization or "").removeprefix("Bearer ").strip()
    if not tokens_match(presented, expected):
        raise ApiError(401, ErrorCode.UNAUTHORIZED, "Invalid service credentials")


def user_token(x_user_authorization: Annotated[str | None, Header()] = None) -> str:
    token = (x_user_authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise ApiError(401, ErrorCode.UNAUTHORIZED, "X-User-Authorization is required")
    return token


def granted_scopes(x_agent_scopes: Annotated[str | None, Header()] = None) -> frozenset[str]:
    """The backend may narrow what the agent can do for this request (e.g. read-only)."""
    if not x_agent_scopes:
        return ALL_SCOPES
    return frozenset(s.strip() for s in x_agent_scopes.split(",")) & ALL_SCOPES


def request_id(request: Request) -> str:
    return request.state.request_id


# --- app -----------------------------------------------------------------------------------------


def create_app(
    settings: Settings | None = None,
    *,
    llm: LLMProvider | None = None,
    backend_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        svc: Services = app.state.services
        logger.info("Agent Core starting", extra={"env": settings.app_env, "llm_provider": svc.llm.name,
                                                  "tools": len(svc.registry)})
        yield
        await svc.llm.aclose()

    is_prod = settings.app_env == "production"
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan,
                  docs_url=None if is_prod else "/docs", redoc_url=None, openapi_url=None if is_prod else "/openapi.json")
    app.state.services = build_services(settings, llm=llm, backend_transport=backend_transport)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request.state.request_id = incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return error_response(exc.status_code, exc.code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return error_response(422, ErrorCode.INVALID_REQUEST, "Request validation failed", details)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException):
        return error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error")
        return error_response(500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred")

    # --- health ---

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["health"])
    async def ready(svc: Svc):
        backend_ok = await BackendClient.ping(svc.settings.backend_api_url, transport=svc.backend_transport)
        llm_ok = svc.llm.name != "unconfigured"
        checks = {"backend": "ok" if backend_ok else "unreachable", "llm": svc.llm.name, "tools": len(svc.registry),
                  "document_search": "backend (pgvector)"}
        ok = backend_ok and llm_ok
        return JSONResponse({"status": "ready" if ok else "not_ready", "checks": checks}, status_code=200 if ok else 503)

    # --- agent ---

    @app.post("/agent/run", response_model=AgentRunResponse, tags=["agent"], dependencies=[Depends(require_service)])
    async def run_agent(
        body: AgentRunRequest, svc: Svc, token: Annotated[str, Depends(user_token)],
        scopes: Annotated[frozenset[str], Depends(granted_scopes)], rid: Annotated[str, Depends(request_id)],
    ):
        async with svc.backend(token, rid) as backend:
            deps = RunDeps(settings=svc.settings, llm=svc.llm, registry=svc.registry, approvals=svc.approvals,
                           memory=svc.memory, backend=backend, scopes=scopes)
            result = await svc.runner.run(body, deps)
        if result.error and result.error.code in (ErrorCode.UNAUTHORIZED, ErrorCode.FORBIDDEN):
            status = 401 if result.error.code == ErrorCode.UNAUTHORIZED else 403
            return JSONResponse(result.model_dump(mode="json"), status_code=status)
        return result

    @app.get("/agent/tools", tags=["agent"], dependencies=[Depends(require_service)])
    async def list_tools(svc: Svc):
        return [
            {"name": t.name, "description": t.description, "domain": t.domain.value, "risk": t.risk.value,
             "permission": t.permission, "requires_approval": t.requires_approval(svc.settings.mutation_policy),
             "input_schema": t.spec().input_schema, "output_schema": t.output_model.model_json_schema()}
            for t in svc.registry.tools()
        ]

    async def _approval_user(backend: BackendClient) -> UserContext:
        try:
            me = await backend.get_me()
            prefs = await backend.get_preferences()
        except BackendAuthError:
            raise ApiError(401, ErrorCode.UNAUTHORIZED, "Your session has expired. Please sign in again.")
        except BackendError:
            raise ApiError(503, ErrorCode.BACKEND_UNAVAILABLE, "It's Personal is unavailable right now.")
        return UserContext(user_id=me.id, name=me.name, timezone=prefs.timezone, currency=prefs.currency,
                           preferences=prefs.model_dump(exclude_none=True))

    def _decision(approval) -> ApprovalDecisionResponse:
        error = AgentError(code=ErrorCode.INTERNAL_ERROR, message=approval.error) if approval.error else None
        return ApprovalDecisionResponse(approval_id=approval.id, status=approval.status.value, result=approval.result, error=error)

    async def _decide(svc: Services, approval_id: str, token: str, rid: str, action: str) -> ApprovalDecisionResponse:
        async with svc.backend(token, rid) as backend:
            user = await _approval_user(backend)
            try:
                if action == "approve":
                    today = datetime.now(ZoneInfo(user.timezone)).date()
                    ctx = ToolContext(backend=backend, user=user, today=today, memory=svc.memory.long_term)
                    approval = await svc.approvals.approve(approval_id, ctx)
                elif action == "reject":
                    approval = await svc.approvals.reject(approval_id, user.user_id)
                else:
                    approval = await svc.approvals.get(approval_id, user.user_id)
            except ApprovalNotFoundError:
                raise ApiError(404, ErrorCode.NOT_FOUND, "Approval not found")
            except ApprovalExpiredError as exc:
                raise ApiError(409, ErrorCode.APPROVAL_EXPIRED, str(exc))
            except ApprovalStateError as exc:
                raise ApiError(409, ErrorCode.INVALID_STATE, str(exc))
        return _decision(approval)

    @app.get("/agent/approvals/{approval_id}", response_model=ApprovalDecisionResponse, tags=["approvals"],
             dependencies=[Depends(require_service)])
    async def get_approval(approval_id: str, svc: Svc, token: Annotated[str, Depends(user_token)], rid: Annotated[str, Depends(request_id)]):
        return await _decide(svc, approval_id, token, rid, "get")

    @app.post("/agent/approvals/{approval_id}/approve", response_model=ApprovalDecisionResponse, tags=["approvals"],
              dependencies=[Depends(require_service)])
    async def approve(approval_id: str, svc: Svc, token: Annotated[str, Depends(user_token)], rid: Annotated[str, Depends(request_id)]):
        return await _decide(svc, approval_id, token, rid, "approve")

    @app.post("/agent/approvals/{approval_id}/reject", response_model=ApprovalDecisionResponse, tags=["approvals"],
              dependencies=[Depends(require_service)])
    async def reject(approval_id: str, svc: Svc, token: Annotated[str, Depends(user_token)], rid: Annotated[str, Depends(request_id)]):
        return await _decide(svc, approval_id, token, rid, "reject")

    class ExecuteIn(BaseModel):
        action_type: str = Field(min_length=1, max_length=100)
        action_payload: dict[str, Any] = Field(default_factory=dict)

    @app.post("/agent/actions/execute", tags=["approvals"], dependencies=[Depends(require_service)])
    async def execute_action(
        body: ExecuteIn, svc: Svc, token: Annotated[str, Depends(user_token)],
        scopes: Annotated[frozenset[str], Depends(granted_scopes)], rid: Annotated[str, Depends(request_id)],
    ):
        """Run one approved action. Only the backend (service token) can call this, after it has
        validated the stored approval (owner, pending, not expired) in its database. The action
        runs with the user's own token, so the backend still authorises the data it touches."""
        tool = svc.registry.get(body.action_type)
        if tool is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, f"Unknown action {body.action_type}")
        async with svc.backend(token, rid) as backend:
            user = await _approval_user(backend)
            today = datetime.now(ZoneInfo(user.timezone)).date()
            ctx = ToolContext(backend=backend, user=user, today=today,
                              memory=svc.memory.long_term, scopes=scopes)
            try:
                result = await svc.registry.execute(tool, tool.parse(body.action_payload), ctx)
            except ToolInputError as exc:
                raise ApiError(422, ErrorCode.INVALID_REQUEST, str(exc))
            except ToolError as exc:
                raise ApiError(409, ErrorCode.INVALID_STATE, str(exc))
        summary = result.get("summary") or result.get("title") or result.get("name") or f"{tool.name} done"
        return {"status": "completed", "action_type": tool.name, "result": result, "summary": str(summary)}

    # --- backend compatibility: AGENT_CORE_MODE=http in the existing backend ---

    class CompleteTool(BaseModel):
        name: str
        description: str = ""
        input_schema: dict[str, Any]

    class CompleteIn(BaseModel):
        system: str = ""
        messages: list[dict[str, Any]] = Field(min_length=1)
        tools: list[CompleteTool] = Field(default_factory=list)

    @app.post("/v1/complete", tags=["compat"], dependencies=[Depends(require_service)])
    async def complete(body: CompleteIn, svc: Svc):
        """One model turn for the backend's own agent loop (tools still execute in the backend)."""
        try:
            result = await svc.llm.invoke(
                system=body.system, messages=body.messages,
                tools=[LLMToolSpec(t.name, t.description, t.input_schema) for t in body.tools],
            )
        except LLMError as exc:
            return error_response(503 if exc.retryable else 502, ErrorCode.LLM_ERROR, exc.message)
        return {"content": result.content, "stop_reason": result.stop_reason, "model": result.model}

    return app
