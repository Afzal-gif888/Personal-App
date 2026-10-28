"""Tests for rate limiting backends: InMemory and Redis."""

from app.core.rate_limit import (
    InMemoryRateLimitBackend,
    RedisRateLimitBackend,
    create_rate_limit_backend,
)
from app.core.config import get_settings


class FakeRedisPipeline:
    def __init__(self, fake_redis):
        self.redis = fake_redis
        self.ops = []

    def incr(self, key):
        self.ops.append(("incr", key))
        return self

    def ttl(self, key):
        self.ops.append(("ttl", key))
        return self

    def execute(self):
        results = []
        for op, key in self.ops:
            if op == "incr":
                val = self.redis.store.get(key, 0) + 1
                self.redis.store[key] = val
                results.append(val)
            elif op == "ttl":
                results.append(self.redis.ttls.get(key, -1))
        return results


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}

    def pipeline(self):
        return FakeRedisPipeline(self)

    def expire(self, key, seconds):
        self.ttls[key] = seconds

    def keys(self, pattern):
        return [k for k in self.store.keys() if k.startswith("rl:")]

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)
            self.ttls.pop(k, None)


def test_in_memory_rate_limit_backend():
    backend = InMemoryRateLimitBackend()
    key = "test_user_1"
    # Limit: 3 requests per 60 seconds
    assert backend.hit(key, limit=3, window_seconds=60) is True
    assert backend.hit(key, limit=3, window_seconds=60) is True
    assert backend.hit(key, limit=3, window_seconds=60) is True
    # 4th request exceeds limit
    assert backend.hit(key, limit=3, window_seconds=60) is False

    backend.reset()
    assert backend.hit(key, limit=3, window_seconds=60) is True


def test_redis_rate_limit_backend():
    fake_redis = FakeRedis()
    backend = RedisRateLimitBackend(fake_redis)
    key = "user_redis_1"

    # Limit: 2 requests per 60 seconds
    assert backend.hit(key, limit=2, window_seconds=60) is True
    assert fake_redis.ttls.get(f"rl:{key}") == 60

    assert backend.hit(key, limit=2, window_seconds=60) is True
    # Exceeds limit
    assert backend.hit(key, limit=2, window_seconds=60) is False

    # Reset
    backend.reset()
    assert f"rl:{key}" not in fake_redis.store
    assert backend.hit(key, limit=2, window_seconds=60) is True


def test_create_rate_limit_backend_selection(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "redis_url", "")
    backend = create_rate_limit_backend()
    assert isinstance(backend, InMemoryRateLimitBackend)
