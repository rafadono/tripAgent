from __future__ import annotations

from fastapi import HTTPException, Request

from tripagent.config import get_settings
from tripagent.guardrails import (
    enforce_rate_limit,
    ensure_costly_endpoints_enabled,
    ensure_plan_endpoint_enabled,
    require_api_key_if_enabled,
)


def guard_costly_endpoint(request: Request, endpoint: str, limit: int) -> None:
    settings = get_settings()
    require_api_key_if_enabled(request, settings)
    enforce_rate_limit(request, endpoint, limit=limit, window_sec=settings.rate_limit_window_sec)
    ensure_costly_endpoints_enabled(settings)


def ensure_plan_enabled() -> None:
    settings = get_settings()
    ensure_plan_endpoint_enabled(settings)


def require_admin_token(request: Request) -> None:
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(status_code=403, detail="Admin token not configured")
    supplied = request.headers.get("X-Admin-Token", "").strip()
    if supplied != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")

