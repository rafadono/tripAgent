from __future__ import annotations

import time

from fastapi import FastAPI, Request

from tripagent.config import get_settings
from tripagent.metrics import METRICS, MetricEvent
from tripagent.persistence import PERSISTENCE
from tripagent.security import extract_session_id
from tripagent.security import resolve_session_user

_SEEN_SESSION_REVENUE: set[str] = set()


def _extract_user_id(request: Request) -> str | None:
    return resolve_session_user(request)


def install_metrics_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        t0 = time.perf_counter()
        status = 500
        settings = get_settings()
        session_id = extract_session_id(request)
        user_id = _extract_user_id(request)
        if not session_id:
            session_id = f"anon-{int(time.time() * 1000)}"
        try:
            response = await call_next(request)
            status = response.status_code
            if not request.cookies.get("tripagent_session_id"):
                response.set_cookie(
                    key="tripagent_session_id",
                    value=session_id,
                    httponly=True,
                    samesite="Lax",
                    secure=request.url.scheme == "https",
                    max_age=60 * 60 * 24 * 30,
                )
            return response
        finally:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            METRICS.record(
                MetricEvent(
                    endpoint=request.url.path,
                    status_code=status,
                    cost_estimate=0.0,
                    cache_hit=False,
                    latency_ms=latency_ms,
                )
            )
            PERSISTENCE.record_business_event(
                endpoint=request.url.path,
                status_code=status,
                session_id=session_id,
                user_id=user_id,
                est_api_cost=0.0,
                est_ads_revenue=settings.est_ads_revenue_per_request if session_id not in _SEEN_SESSION_REVENUE else 0.0,
                latency_ms=latency_ms,
                meta={"method": request.method},
            )
            _SEEN_SESSION_REVENUE.add(session_id)
