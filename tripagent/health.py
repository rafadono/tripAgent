# tripagent/health.py
"""
Health endpoints following the Health Check Response Format standard (draft-inadarei-api-health-check).
https://datatracker.ietf.org/doc/html/draft-inadarei-api-health-check

GET /health/live   → liveness:  is the process alive?
GET /health/ready  → readiness: can it handle real requests?
GET /health        → alias of /health/ready (Docker/k8s compatibility)
"""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Response
from pydantic import BaseModel

from tripagent.config import get_settings
from tripagent.health_checker import (
    ComponentCheck,
    check_api_key,
    check_google_places,
    check_google_routes,
)

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    status: str                          # "pass" | "warn" | "fail"
    version: str = "0.1.0"
    description: str = "TripAgent API"
    checks: Dict[str, ComponentCheck] = {}


def _overall_status(checks: Dict[str, ComponentCheck]) -> str:
    """
    Aggregation rule:
      - Any "fail"  → "fail"
      - Any "warn"  → "warn"
      - All "pass"  → "pass"
    """
    statuses = {c.status for c in checks.values()}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def _http_status_code(status: str) -> int:
    """
    Standard state to HTTP status code mapping:
      pass → 200
      warn → 200  (service operational with warnings)
      fail → 503  (Service Unavailable)
    """
    return 503 if status == "fail" else 200


@router.get("/live", summary="Liveness probe")
def liveness():
    """
    Verifies that the process is alive.
    Only fails if the application crashed completely.
    Used by Docker/k8s to decide whether to restart the container.
    """
    return {"status": "pass", "description": "process active"}


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
)
def readiness(response: Response):
    """
    Verifies that the service can handle real requests:
    - GOOGLE_MAPS_API_KEY configured
    - Google Places API accessible and authorized
    - Google Routes API accessible and authorized

    Returns HTTP 200 if everything is fine (or warnings),
    HTTP 503 if any critical component fails.
    """
    settings = get_settings()
    checks: Dict[str, ComponentCheck] = {"google_api_key": check_api_key()}
    if settings.health_check_upstream_enabled:
        checks["google_places_api"] = check_google_places()
        checks["google_routes_api"] = check_google_routes()
    else:
        checks["google_places_api"] = ComponentCheck(
            status="warn",
            output="Upstream checks disabled by TRIPAGENT_HEALTH_CHECK_UPSTREAM_ENABLED",
        )
        checks["google_routes_api"] = ComponentCheck(
            status="warn",
            output="Upstream checks disabled by TRIPAGENT_HEALTH_CHECK_UPSTREAM_ENABLED",
        )

    status = _overall_status(checks)
    response.status_code = _http_status_code(status)

    return HealthResponse(status=status, checks=checks)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check (alias of /ready)",
)
def health_alias(response: Response):
    """Alias of /health/ready for Docker HEALTHCHECK compatibility."""
    return readiness(response)
