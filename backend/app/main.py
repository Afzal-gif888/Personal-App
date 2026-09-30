import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import error_body, register_exception_handlers
from app.core.logging import configure_logging, request_id_var
from app.db.session import check_database
from app.llm import get_provider

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    provider = get_provider()
    logger.info("Starting API", extra={"env": settings.app_env, "llm_provider": provider.name})
    scheduler = None
    if settings.scheduler_enabled:
        from app.jobs.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.start()
    yield
    if scheduler:
        scheduler.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.app_env == "production" else "/docs",
        redoc_url=None,
        openapi_url=None if settings.app_env == "production" else "/openapi.json",
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if not request.url.path.startswith(("/docs", "/openapi.json", "/redoc")):
            # API responses are data, never pages: nothing may load from or frame them.
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response

    # Origins aren't secrets: logging them shows at a glance whether CORS_ORIGINS reached the app.
    logger.info("CORS allowed origins", extra={"origins": settings.cors_origins,
                                                "origin_regex": settings.cors_origin_regex or None})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=False,  # bearer tokens, not cookies
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready():
        try:
            check_database()
        except Exception:
            logger.exception("Readiness check failed")
            return JSONResponse(error_body("NOT_READY", "Database unavailable"), status_code=503)
        return {"status": "ready", "llm": get_provider().name}

    return app


app = create_app()
