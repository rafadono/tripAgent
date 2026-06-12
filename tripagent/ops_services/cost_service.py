from __future__ import annotations

import math
import time
from typing import Any

from tripagent.budget import endpoint_unit_cost, estimate_daily_cost, simulate_cost_projection
from tripagent.config import AppSettings
from tripagent.metrics import METRICS
from tripagent.persistence import PERSISTENCE


class OpsCostService:
    @staticmethod
    def cache_unit_cost(settings: AppSettings, upstream_name: str) -> float:
        return {
            "places.search_text": settings.estimate_cost_places_text_search,
            "places.search_nearby": settings.estimate_cost_places_nearby,
            "places.details": settings.estimate_cost_places_details,
            "routes.matrix": settings.estimate_cost_routes_matrix,
            "routes.polyline": settings.estimate_cost_routes_polyline,
        }.get(upstream_name, 0.0)

    def metrics(self) -> dict[str, Any]:
        return {
            "runtime": METRICS.snapshot(),
            "business": PERSISTENCE.business_snapshot(),
        }

    def budget_alerts(self, settings: AppSettings) -> dict[str, Any]:
        return estimate_daily_cost(settings)

    def cost_forecast(self, settings: AppSettings, baseline_daily_requests: int, horizon_days: int) -> dict[str, Any]:
        scenarios = {
            "low": simulate_cost_projection(
                settings,
                baseline_daily_requests=baseline_daily_requests,
                scenario_multiplier=0.6,
                horizon_days=horizon_days,
            ),
            "medium": simulate_cost_projection(
                settings,
                baseline_daily_requests=baseline_daily_requests,
                scenario_multiplier=1.0,
                horizon_days=horizon_days,
            ),
            "high": simulate_cost_projection(
                settings,
                baseline_daily_requests=baseline_daily_requests,
                scenario_multiplier=1.8,
                horizon_days=horizon_days,
            ),
        }
        return {
            "generated_at_unix": int(time.time()),
            "horizon_days": horizon_days,
            "scenarios": scenarios,
        }

    def workload_replay(
        self,
        settings: AppSettings,
        *,
        since_hours: int,
        multiplier: float,
    ) -> dict[str, Any]:
        since_unix = int(time.time()) - (since_hours * 3600)
        snapshot = PERSISTENCE.business_snapshot_since(since_unix)
        rows = snapshot.get("by_endpoint", [])
        replay_rows: list[dict[str, Any]] = []
        total_requests = 0
        total_cost = 0.0
        weighted_latency = 0.0
        for row in rows:
            endpoint = str(row.get("endpoint", ""))
            original_requests = int(row.get("requests", 0))
            replay_requests = int(math.ceil(original_requests * multiplier))
            unit_cost = endpoint_unit_cost(settings, endpoint)
            est_cost = replay_requests * unit_cost
            avg_latency = float(row.get("avg_latency_ms", 0.0))
            total_requests += replay_requests
            total_cost += est_cost
            weighted_latency += replay_requests * avg_latency
            replay_rows.append(
                {
                    "endpoint": endpoint,
                    "original_requests": original_requests,
                    "replay_requests": replay_requests,
                    "avg_latency_ms": round(avg_latency, 2),
                    "unit_cost": round(unit_cost, 6),
                    "estimated_cost": round(est_cost, 6),
                }
            )
        avg_latency_replay = (weighted_latency / total_requests) if total_requests else 0.0
        return {
            "since_hours": since_hours,
            "multiplier": multiplier,
            "replay": replay_rows,
            "summary": {
                "projected_requests": total_requests,
                "estimated_api_cost": round(total_cost, 6),
                "projected_avg_latency_ms": round(avg_latency_replay, 2),
            },
        }

    def cache_efficiency(self, settings: AppSettings) -> dict[str, Any]:
        upstream = METRICS.snapshot().get("upstream", {})
        calls = upstream.get("calls", {})
        cache_hits = upstream.get("cache_hits", {})
        observed_costs = upstream.get("estimated_cost", {})
        rows = []
        total_uncached = 0.0
        total_observed = 0.0
        for name, n_calls in calls.items():
            call_count = int(n_calls)
            hit_count = int(cache_hits.get(name, 0))
            unit_cost = float(self.cache_unit_cost(settings, str(name)))
            uncached = call_count * unit_cost
            observed = float(observed_costs.get(name, 0.0))
            saved = max(0.0, uncached - observed)
            total_uncached += uncached
            total_observed += observed
            rows.append(
                {
                    "upstream": name,
                    "calls": call_count,
                    "cache_hits": hit_count,
                    "cache_hit_rate": round((hit_count / call_count), 4) if call_count else 0.0,
                    "unit_cost": round(unit_cost, 6),
                    "uncached_cost": round(uncached, 6),
                    "observed_cost": round(observed, 6),
                    "estimated_savings": round(saved, 6),
                }
            )
        rows.sort(key=lambda r: r["estimated_savings"], reverse=True)
        return {
            "rows": rows,
            "totals": {
                "uncached_cost": round(total_uncached, 6),
                "observed_cost": round(total_observed, 6),
                "estimated_savings": round(max(0.0, total_uncached - total_observed), 6),
            },
        }
