from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from tripagent.config import AppSettings
from tripagent.budget import maybe_apply_budget_fallback
from tripagent.runtime_flags import RUNTIME_FLAGS


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_sec: int) -> tuple[bool, int]:
        now = time.time()
        boundary = now - window_sec
        with self._lock:
            dq = self._calls[key]
            while dq and dq[0] < boundary:
                dq.popleft()
            if len(dq) >= limit:
                return False, 0
            dq.append(now)
            remaining = max(0, limit - len(dq))
            return True, remaining


RATE_LIMITER = SlidingWindowRateLimiter()


def client_identity(request: Request) -> str:
    api_key = request.headers.get("X-API-Key", "").strip()
    if api_key:
        return f"key:{api_key}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def require_api_key_if_enabled(request: Request, settings: AppSettings) -> None:
    if not settings.require_api_key:
        return
    supplied = request.headers.get("X-API-Key", "").strip()
    if not supplied:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    if supplied not in settings.api_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")


def enforce_rate_limit(
    request: Request,
    endpoint_key: str,
    limit: int,
    window_sec: int,
) -> None:
    identity = client_identity(request)
    bucket = f"{endpoint_key}:{identity}"
    allowed, _remaining = RATE_LIMITER.allow(bucket, limit=limit, window_sec=window_sec)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def ensure_costly_endpoints_enabled(settings: AppSettings) -> None:
    budget_status = maybe_apply_budget_fallback(settings)
    if settings.budget_auto_fallback and budget_status.get("level") == "exceeded":
        raise HTTPException(
            status_code=503,
            detail="Presupuesto diario excedido: endpoints costosos pausados.",
        )
    if settings.fallback_mode_enabled:
        raise HTTPException(
            status_code=503,
            detail=settings.fallback_message,
        )
    if RUNTIME_FLAGS.costly_enabled(settings):
        return
    raise HTTPException(
        status_code=503,
        detail=settings.fallback_message,
    )


def ensure_plan_endpoint_enabled(settings: AppSettings) -> None:
    if RUNTIME_FLAGS.plan_enabled(settings):
        return
    raise HTTPException(
        status_code=503,
        detail=settings.fallback_message,
    )
