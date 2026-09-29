"""Rate limiting abstraction.

The in-memory backend is per-process and fine for a single API instance. Swap in a
shared backend (e.g. Redis) by implementing `RateLimitBackend` when scaling out.
"""

import threading
import time
from abc import ABC, abstractmethod

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimited


class RateLimitBackend(ABC):
    @abstractmethod
    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record a hit; return False when the key is over its limit."""

    def reset(self) -> None:  # pragma: no cover - optional
        pass


class InMemoryRateLimitBackend(RateLimitBackend):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[float, int]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            start, count = self._windows.get(key, (now, 0))
            if now - start >= window_seconds:
                start, count = now, 0
            count += 1
            self._windows[key] = (start, count)
            return count <= limit

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


backend: RateLimitBackend = InMemoryRateLimitBackend()


def rate_limit(scope: str, per_minute_setting: str):
    """FastAPI dependency factory: limits by client IP per scope."""

    def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        limit = getattr(settings, per_minute_setting)
        client = request.client.host if request.client else "unknown"
        if not backend.hit(f"{scope}:{client}", limit, 60):
            raise RateLimited("Too many requests, please slow down")

    return dependency
