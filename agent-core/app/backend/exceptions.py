"""Backend client errors. Messages are safe to show; response bodies are never included verbatim."""


class BackendError(Exception):
    status_code: int | None = None
    retryable = False

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class BackendUnavailableError(BackendError):
    """Network failure, timeout or 5xx."""

    retryable = True


class BackendAuthError(BackendError):
    """401/403: the user token is missing, expired or not allowed."""


class BackendNotFoundError(BackendError):
    pass


class BackendValidationError(BackendError):
    """422/400: the backend rejected the payload. `details` explains which fields."""

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None, details=None):
        super().__init__(message, status_code=status_code, code=code)
        self.details = details


class BackendRateLimitError(BackendError):
    retryable = True
