from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class MetricEvent:
    endpoint: str
    status_code: int
    cost_estimate: float
    cache_hit: bool
    latency_ms: float


class MetricsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_cost_estimate = 0.0
        self._cache_hits = 0
        self._by_endpoint: dict[str, int] = defaultdict(int)
        self._status_codes: dict[int, int] = defaultdict(int)
        self._sum_latency_ms = 0.0
        self._events: list[MetricEvent] = []
        self._upstream_calls: dict[str, int] = defaultdict(int)
        self._upstream_cost_estimate: dict[str, float] = defaultdict(float)
        self._upstream_cache_hits: dict[str, int] = defaultdict(int)

    def record(self, event: MetricEvent) -> None:
        with self._lock:
            self._total_requests += 1
            self._total_cost_estimate += max(0.0, event.cost_estimate)
            self._cache_hits += 1 if event.cache_hit else 0
            self._by_endpoint[event.endpoint] += 1
            self._status_codes[event.status_code] += 1
            self._sum_latency_ms += max(0.0, event.latency_ms)
            self._events.append(event)
            if len(self._events) > 5000:
                self._events = self._events[-5000:]

    def record_upstream(self, name: str, cost_estimate: float, cache_hit: bool) -> None:
        with self._lock:
            self._upstream_calls[name] += 1
            self._upstream_cost_estimate[name] += max(0.0, cost_estimate)
            self._upstream_cache_hits[name] += 1 if cache_hit else 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total = self._total_requests
            avg_latency = (self._sum_latency_ms / total) if total else 0.0
            cache_rate = (self._cache_hits / total) if total else 0.0
            return {
                "generated_at_unix": int(time.time()),
                "totals": {
                    "requests": total,
                    "estimated_cost": round(self._total_cost_estimate, 6),
                    "cache_hit_rate": round(cache_rate, 4),
                    "avg_latency_ms": round(avg_latency, 2),
                },
                "by_endpoint": dict(self._by_endpoint),
                "status_codes": dict(self._status_codes),
                "upstream": {
                    "calls": dict(self._upstream_calls),
                    "cache_hits": dict(self._upstream_cache_hits),
                    "estimated_cost": {
                        k: round(v, 6) for k, v in self._upstream_cost_estimate.items()
                    },
                    "cache_hit_rate": {
                        k: round(self._upstream_cache_hits[k] / self._upstream_calls[k], 4)
                        for k in self._upstream_calls
                        if self._upstream_calls[k] > 0
                    },
                },
            }


METRICS = MetricsStore()
