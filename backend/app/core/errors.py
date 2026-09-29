"""Domain exceptions and the handlers that render them in the standard error envelope."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str | None = None, *, code: str | None = None, details=None):
        self.message = message or self.__class__.__doc__ or "Request failed"
        if code:
            self.code = code
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    """Resource not found"""

    status_code = 404
    code = "RESOURCE_NOT_FOUND"


class ValidationFailed(AppError):
    """Validation failed"""

    status_code = 422
    code = "VALIDATION_ERROR"


class ConflictError(AppError):
    """Resource conflict"""

    status_code = 409
    code = "CONFLICT"


class AuthenticationError(AppError):
    """Authentication required"""

    status_code = 401
    code = "UNAUTHENTICATED"


class PermissionDenied(AppError):
    """Permission denied"""

    status_code = 403
    code = "FORBIDDEN"


class OtpError(AppError):
    """The sign-in code is invalid."""

    status_code = 400
    code = "OTP_INVALID"


class EmailDeliveryError(AppError):
    """The email could not be sent."""

    status_code = 503
    code = "EMAIL_DELIVERY_FAILED"


class RateLimited(AppError):
    """Too many requests"""

    status_code = 429
    code = "RATE_LIMITED"


class UpstreamError(AppError):
    """Upstream service failed"""

    status_code = 502
    code = "UPSTREAM_ERROR"


_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


def error_body(code: str, message: str, details=None) -> dict:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(error_body(exc.code, exc.message, exc.details), exc.status_code, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(error_body(code, message), exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(error_body("VALIDATION_ERROR", "Request validation failed", details), 422)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(error_body("INTERNAL_ERROR", "An unexpected error occurred"), 500)
