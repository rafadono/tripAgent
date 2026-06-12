from __future__ import annotations

from datetime import datetime
from math import ceil
from time import time
from typing import Any

from tripagent.config import AppSettings
from tripagent.persistence import PERSISTENCE
from tripagent.runtime_flags import RUNTIME_FLAGS


def endpoint_unit_cost(settings: AppSettings, endpoint: str) -> float:
    endpoint = endpoint.lower()
    if endpoint.endswith("/search_places"):
        return max(0.0, settings.estimate_cost_places_text_search)
    if endpoint.endswith("/nearest_parking"):
        return max(0.0, settings.estimate_cost_places_nearby * 2)
    if endpoint.endswith("/plan/alternatives"):
        plan_cost = (
            settings.estimate_cost_routes_matrix
            + settings.estimate_cost_routes_polyline
            + (settings.estimate_cost_places_details * 5)
        )
        return max(0.0, plan_cost * 3)
    if endpoint.endswith("/plan/replan") or endpoint.endswith("/plan"):
        plan_cost = (
            settings.estimate_cost_routes_matrix
            + settings.estimate_cost_routes_polyline
            + (settings.estimate_cost_places_details * 5)
        )
        return max(0.0, plan_cost)
    return 0.0


def estimate_daily_cost(settings: AppSettings) -> dict[str, Any]:
    now = datetime.now()
    start_day = datetime(now.year, now.month, now.day).timestamp()
    snapshot = PERSISTENCE.business_snapshot_since(int(start_day))
    endpoint_rows = snapshot.get("by_endpoint", [])
    total = 0.0
    details: list[dict[str, Any]] = []
    for row in endpoint_rows:
        endpoint = str(row.get("endpoint", ""))
        requests = int(row.get("requests", 0))
        unit_cost = endpoint_unit_cost(settings, endpoint)
        est = round(requests * unit_cost, 6)
        total += est
        details.append(
            {
                "endpoint": endpoint,
                "requests": requests,
                "unit_cost": round(unit_cost, 6),
                "estimated_cost": est,
            }
        )
    limit = max(0.0, float(settings.daily_budget_limit))
    utilization = (total / limit) if limit > 0 else 0.0
    warn = max(0.0, float(settings.budget_alert_threshold_warn))
    critical = max(warn, float(settings.budget_alert_threshold_critical))
    if limit <= 0:
        level = "disabled"
    elif utilization >= 1.0:
        level = "exceeded"
    elif utilization >= critical:
        level = "critical"
    elif utilization >= warn:
        level = "warn"
    else:
        level = "ok"

    return {
        "generated_at_unix": int(time()),
        "daily_budget_limit": round(limit, 6),
        "estimated_daily_cost": round(total, 6),
        "utilization": round(utilization, 4),
        "level": level,
        "by_endpoint": details,
    }


def maybe_apply_budget_fallback(settings: AppSettings) -> dict[str, Any]:
    status = estimate_daily_cost(settings)
    should_cut = settings.budget_auto_fallback and status.get("level") == "exceeded"
    if should_cut:
        RUNTIME_FLAGS.set_costly_enabled(False)
        RUNTIME_FLAGS.set_plan_enabled(False)
        status["auto_fallback_applied"] = True
    else:
        status["auto_fallback_applied"] = False
    return status


def simulate_cost_projection(
    settings: AppSettings,
    *,
    baseline_daily_requests: int,
    scenario_multiplier: float,
    horizon_days: int,
) -> dict[str, Any]:
    multiplier = max(0.0, float(scenario_multiplier))
    days = max(1, int(horizon_days))
    daily_requests = int(ceil(max(0, baseline_daily_requests) * multiplier))
    avg_cost_per_request = (
        endpoint_unit_cost(settings, "/plan") * 0.45
        + endpoint_unit_cost(settings, "/search_places") * 0.35
        + endpoint_unit_cost(settings, "/nearest_parking") * 0.20
    )
    daily_cost = round(daily_requests * avg_cost_per_request, 6)
    weekly_cost = round(daily_cost * 7, 6)
    horizon_cost = round(daily_cost * days, 6)
    return {
        "baseline_daily_requests": baseline_daily_requests,
        "scenario_multiplier": round(multiplier, 3),
        "projected_daily_requests": daily_requests,
        "estimated_cost_per_request": round(avg_cost_per_request, 6),
        "estimated_daily_cost": daily_cost,
        "estimated_weekly_cost": weekly_cost,
        "estimated_horizon_cost": horizon_cost,
        "horizon_days": days,
    }
