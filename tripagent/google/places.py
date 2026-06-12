import asyncio
from typing import Any, Dict

import httpx

from tripagent.cache import build_cache_key, cached_call, get_cache_backend
from tripagent.config import get_settings, require_google_key
from tripagent.http_client import get_session
from tripagent.metrics import METRICS

def place_details(place_id: str, fields: str) -> Dict[str, Any]:
    """
    Places Details (New):
    GET https://places.googleapis.com/v1/places/{place_id}?fields=...&key=...
    """
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    params = {"fields": fields, "key": require_google_key()}
    settings = get_settings()

    def _loader() -> Dict[str, Any]:
        r = get_session().get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    data, cache_hit = cached_call(
        prefix="places.details",
        payload={"place_id": place_id, "fields": fields},
        ttl_sec=settings.cache_ttl_place_details_sec,
        loader=_loader,
    )
    METRICS.record_upstream(
        "places.details",
        cost_estimate=settings.estimate_cost_places_details if not cache_hit else 0.0,
        cache_hit=cache_hit,
    )
    return data


async def _place_details_fetch_async(
    client: httpx.AsyncClient,
    place_id: str,
    fields: str,
) -> Dict[str, Any]:
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    params = {"fields": fields, "key": require_google_key()}
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


async def _place_details_many_async(
    missing_ids: list[str],
    fields: str,
    max_concurrency: int,
) -> dict[str, Dict[str, Any]]:
    timeout = httpx.Timeout(30.0)
    limits = httpx.Limits(max_connections=max(8, max_concurrency), max_keepalive_connections=max(8, max_concurrency))
    semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        async def _guarded_fetch(pid: str) -> tuple[str, Dict[str, Any]]:
            async with semaphore:
                data = await _place_details_fetch_async(client, pid, fields)
                return pid, data

        pairs = await asyncio.gather(*(_guarded_fetch(pid) for pid in missing_ids))
    return {pid: data for pid, data in pairs}


def place_details_many(place_ids: list[str], fields: str, max_concurrency: int = 8) -> dict[str, Dict[str, Any]]:
    settings = get_settings()
    backend = get_cache_backend()
    unique_ids = list(dict.fromkeys(place_ids))
    by_id: dict[str, Dict[str, Any]] = {}
    missing: list[str] = []

    for pid in unique_ids:
        key = build_cache_key("places.details", {"place_id": pid, "fields": fields})
        cached = backend.get(key) if settings.cache_enabled else None
        if cached is not None:
            by_id[pid] = cached
            METRICS.record_upstream("places.details", cost_estimate=0.0, cache_hit=True)
        else:
            missing.append(pid)

    if missing:
        try:
            loop = asyncio.get_running_loop()
            loop_running = loop.is_running()
        except RuntimeError:
            loop_running = False
        if loop_running:
            fetched = {pid: place_details(pid, fields) for pid in missing}
        else:
            fetched = asyncio.run(_place_details_many_async(missing, fields, max_concurrency=max_concurrency))
        for pid, data in fetched.items():
            by_id[pid] = data
            if settings.cache_enabled:
                key = build_cache_key("places.details", {"place_id": pid, "fields": fields})
                backend.set(key, data, settings.cache_ttl_place_details_sec)
            METRICS.record_upstream(
                "places.details",
                cost_estimate=settings.estimate_cost_places_details,
                cache_hit=False,
            )
    return by_id
