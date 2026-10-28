"""Rate limiting abstraction.

The in-memory backend is per-process and fine for a single API instance. Swap in a
shared backend (e.g. Redis) by implementing `RateLimitBackend` when scaling out.
"""

import threading
import time
from abc import ABC, abstractmethod

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AuthenticationError, RateLimited
from app.core.security import decode_access_token


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


import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisRateLimitBackend(RateLimitBackend):
    """Distributed rate limiting backend using Redis key expiration."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        redis_key = f"rl:{key}"
        try:
            pipe = self.redis.pipeline()
            pipe.incr(redis_key)
            pipe.ttl(redis_key)
            results = pipe.execute()
            count, ttl = int(results[0]), int(results[1])
            if ttl == -1 or count == 1:
                self.redis.expire(redis_key, window_seconds)
            return count <= limit
        except Exception as exc:
            logger.warning("Redis rate limit failed, allowing request", extra={"error": str(exc)})
            return True

    def reset(self) -> None:
        try:
            keys = self.redis.keys("rl:*")
            if keys:
                self.redis.delete(*keys)
        except Exception:
            pass


def create_rate_limit_backend() -> RateLimitBackend:
    """Create the configured backend: Redis if redis_url is set, else InMemory."""
    settings = get_settings()
    if settings.redis_url:
        try:
            import redis
            client = redis.Redis.from_url(settings.redis_url)
            return RedisRateLimitBackend(client)
        except ImportError:
            logger.warning("redis package not installed, falling back to InMemoryRateLimitBackend")
            return InMemoryRateLimitBackend()
        except Exception as exc:
            logger.warning("Could not connect to Redis, falling back to InMemoryRateLimitBackend: %s", exc)
            return InMemoryRateLimitBackend()
    return InMemoryRateLimitBackend()

backend: RateLimitBackend = InMemoryRateLimitBackend()


def rate_limit(scope: str, per_minute_setting: str):
    """FastAPI dependency factory: limits per signed-in user, or per client IP when anonymous.

    Keying signed-in requests by user matters in production: Agent Core calls the API for every
    student from one IP, and many students can share a campus IP."""

    def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        limit = getattr(settings, per_minute_setting)
        if not backend.hit(f"{scope}:{_caller(request)}", limit, 60):
            raise RateLimited("Too many requests, please slow down")

    return dependency


def _caller(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            return f"user:{decode_access_token(auth[7:].strip())['sub']}"
        except AuthenticationError:  # invalid/expired: the endpoint rejects it; count it by IP here
            pass
    return f"ip:{request.client.host if request.client else 'unknown'}"
