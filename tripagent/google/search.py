# tripagent/google/search.py
import math
from typing import Any, Dict, List

from tripagent.cache import cached_call
from tripagent.config import require_google_key
from tripagent.config import get_settings
from tripagent.http_client import get_session
from tripagent.metrics import METRICS

_PLACES_BASE = "https://places.googleapis.com/v1/places"


def text_search(query: str, *, max_results: int = 5) -> List[Dict[str, Any]]:
    """Places Text Search (New API)."""
    url = f"{_PLACES_BASE}:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": require_google_key(),
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location",
    }
    settings = get_settings()

    def _loader() -> List[Dict[str, Any]]:
        r = get_session().post(url, headers=headers, json={"textQuery": query}, timeout=30)
        r.raise_for_status()
        return r.json().get("places") or []

    places, cache_hit = cached_call(
        prefix="places.search_text",
        payload={"query": query},
        ttl_sec=settings.cache_ttl_text_search_sec,
        loader=_loader,
    )
    METRICS.record_upstream(
        "places.search_text",
        cost_estimate=settings.estimate_cost_places_text_search if not cache_hit else 0.0,
        cache_hit=cache_hit,
    )
    return places[:max_results]


def nearby_search(
    lat: float,
    lng: float,
    *,
    included_types: List[str],
    max_results: int = 10,
    radius_m: float = 800,
) -> List[Dict[str, Any]]:
    """
    Places Nearby Search (New API).
    https://places.googleapis.com/v1/places:searchNearby
    """
    url = f"{_PLACES_BASE}:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": require_google_key(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.priceLevel,places.types,"
            "places.regularOpeningHours"
        ),
    }
    body = {
        "includedTypes": included_types,
        "maxResultCount": min(max_results, 20),
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_m,
            }
        },
    }
    settings = get_settings()

    def _loader() -> List[Dict[str, Any]]:
        r = get_session().post(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json().get("places") or []

    places, cache_hit = cached_call(
        prefix="places.search_nearby",
        payload={
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "types": included_types,
            "radius_m": radius_m,
            "max_results": max_results,
        },
        ttl_sec=settings.cache_ttl_nearby_search_sec,
        loader=_loader,
    )
    METRICS.record_upstream(
        "places.search_nearby",
        cost_estimate=settings.estimate_cost_places_nearby if not cache_hit else 0.0,
        cache_hit=cache_hit,
    )
    return places


def resolve_place_id(query: str) -> str:
    places = text_search(query, max_results=1)
    if not places:
        raise ValueError(f"No results for query: {query}")
    pid = places[0].get("id")
    if not pid:
        raise ValueError(f"Search result missing id for query: {query}")
    return pid


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in meters between two lat/lng points."""
    earth_radius_m = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return earth_radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def walk_minutes(distance_m: float, speed_kmh: float = 5.0) -> int:
    """Estimated walking time in minutes."""
    return max(1, round(distance_m / (speed_kmh * 1000 / 60)))


# Parking hourly estimate tiers (Santiago reference, CLP/h)
_PRICE_TIERS = [
    (200, 4_500, "Premium (zona centrica)"),
    (400, 3_200, "Alta demanda"),
    (700, 2_400, "Estandar"),
    (9999, 1_600, "Periferia"),
]


def estimate_parking_cost_clp(distance_to_poi_m: float) -> Dict[str, Any]:
    """Return estimated hourly cost and tier label for parking at given distance."""
    for max_dist, price, label in _PRICE_TIERS:
        if distance_to_poi_m <= max_dist:
            return {"price_clp_hr": price, "tier": label}
    return {"price_clp_hr": 1_600, "tier": "Periferia"}
