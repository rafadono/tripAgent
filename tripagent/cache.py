from __future__ import annotations

import hashlib
import threading
import time
from typing import Any, Callable, Protocol

from tripagent.config import get_settings
from tripagent.jsonx import dumps_str, loads


class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None:
        ...

    def set(self, key: str, value: Any, ttl_sec: int) -> None:
        ...


class MemoryTTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_sec: int) -> None:
        expires_at = time.time() + max(1, ttl_sec)
        with self._lock:
            self._store[key] = (expires_at, value)


class RedisTTLCache:
    def __init__(self, redis_url: str) -> None:
        import redis  # optional dependency

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> Any | None:
        payload = self._client.get(key)
        if payload is None:
            return None
        return loads(payload)

    def set(self, key: str, value: Any, ttl_sec: int) -> None:
        self._client.setex(key, max(1, ttl_sec), dumps_str(value))


_CACHE_BACKEND: CacheBackend | None = None


def _create_backend() -> CacheBackend:
    settings = get_settings()
    if settings.cache_backend == "redis" and settings.cache_redis_url:
        try:
            return RedisTTLCache(settings.cache_redis_url)
        except Exception:
            return MemoryTTLCache()
    return MemoryTTLCache()


def get_cache_backend() -> CacheBackend:
    global _CACHE_BACKEND
    if _CACHE_BACKEND is None:
        _CACHE_BACKEND = _create_backend()
    return _CACHE_BACKEND


def build_cache_key(prefix: str, payload: dict[str, Any]) -> str:
    serialized = dumps_str(payload, sort_keys=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"tripagent:{prefix}:{digest}"


def cached_call(
    prefix: str,
    payload: dict[str, Any],
    ttl_sec: int,
    loader: Callable[[], Any],
) -> tuple[Any, bool]:
    settings = get_settings()
    if not settings.cache_enabled:
        return loader(), False

    key = build_cache_key(prefix, payload)
    backend = get_cache_backend()
    value = backend.get(key)
    if value is not None:
        return value, True

    value = loader()
    backend.set(key, value, ttl_sec)
    return value, False
