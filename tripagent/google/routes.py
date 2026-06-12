from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from tripagent.cache import cached_call
from tripagent.config import get_settings, require_google_key
from tripagent.http_client import get_session
from tripagent.jsonx import dumps_bytes, loads
from tripagent.metrics import METRICS


def _parse_route_matrix_response(text: str) -> List[Dict[str, Any]]:
    text = text.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            return loads(text)
        except Exception:
            pass
    elements = []
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if line and line not in ("[", "]"):
            try:
                elements.append(loads(line))
            except Exception:
                continue
    return elements


def _parse_distance_matrix_response(
    data: Dict[str, Any],
    n_origins: int,
    n_dests: int,
) -> List[Dict[str, Any]]:
    _ = (n_origins, n_dests)
    elements = []
    rows = data.get("rows", [])
    for oi, row in enumerate(rows):
        for di, el in enumerate(row.get("elements", [])):
            status = el.get("status", "")
            dur_sec = el.get("duration", {}).get("value", 0) if status == "OK" else 999_999
            dist_m = el.get("distance", {}).get("value", 0) if status == "OK" else 999_999
            elements.append(
                {
                    "originIndex": oi,
                    "destinationIndex": di,
                    "duration": {"seconds": str(dur_sec)},
                    "distanceMeters": dist_m,
                    "status": {"code": 0} if status == "OK" else {"code": 4},
                    "condition": "ROUTE_EXISTS" if status == "OK" else "ROUTE_NOT_FOUND",
                }
            )
    return elements


def _compute_route_matrix_drive_walk(
    origins: List[Dict[str, Any]],
    destinations: List[Dict[str, Any]],
    travel_mode: str,
    routing_preference: Optional[str] = None,
) -> List[Dict[str, Any]]:
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": require_google_key(),
        "X-Goog-FieldMask": "originIndex,destinationIndex,status,condition,distanceMeters,duration",
    }
    body: Dict[str, Any] = {
        "origins": [{"waypoint": o} for o in origins],
        "destinations": [{"waypoint": d} for d in destinations],
        "travelMode": travel_mode,
    }
    if routing_preference:
        body["routingPreference"] = routing_preference

    response = get_session().post(url, headers=headers, data=dumps_bytes(body), timeout=60)
    response.raise_for_status()
    return _parse_route_matrix_response(response.text)


def _latlng_str(wp: Dict[str, Any]) -> str:
    ll = wp.get("location", {}).get("latLng", {})
    return f"{ll['latitude']},{ll['longitude']}"


def _compute_route_matrix_transit(
    origins: List[Dict[str, Any]],
    destinations: List[Dict[str, Any]],
    departure_time: Optional[int] = None,
) -> List[Dict[str, Any]]:
    origins_str = "|".join(_latlng_str(o) for o in origins)
    dests_str = "|".join(_latlng_str(d) for d in destinations)

    params: Dict[str, Any] = {
        "origins": origins_str,
        "destinations": dests_str,
        "mode": "transit",
        "transit_mode": "bus|subway|rail",
        "key": require_google_key(),
        "language": "es",
    }
    params["departure_time"] = (
        departure_time if departure_time else int(datetime.now(timezone.utc).timestamp())
    )

    response = get_session().get(
        "https://maps.googleapis.com/maps/api/distancematrix/json",
        params=params,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(
            f"Distance Matrix API error: {data.get('status')} - {data.get('error_message', '')}"
        )

    return _parse_distance_matrix_response(data, len(origins), len(destinations))


def compute_route_matrix(
    origins: List[Dict[str, Any]],
    destinations: List[Dict[str, Any]],
    travel_mode: str,
    routing_preference: Optional[str] = None,
    departure_time: Optional[int] = None,
) -> List[Dict[str, Any]]:
    settings = get_settings()

    def _loader() -> List[Dict[str, Any]]:
        if travel_mode == "TRANSIT":
            return _compute_route_matrix_transit(origins, destinations, departure_time)
        return _compute_route_matrix_drive_walk(origins, destinations, travel_mode, routing_preference)

    elements, cache_hit = cached_call(
        prefix="routes.matrix",
        payload={
            "origins": origins,
            "destinations": destinations,
            "travel_mode": travel_mode,
            "routing_preference": routing_preference,
            "departure_time": departure_time,
        },
        ttl_sec=settings.cache_ttl_route_matrix_sec,
        loader=_loader,
    )
    METRICS.record_upstream(
        "routes.matrix",
        cost_estimate=settings.estimate_cost_routes_matrix if not cache_hit else 0.0,
        cache_hit=cache_hit,
    )
    return elements


def compute_polyline(
    origin: Dict[str, Any],
    destination: Dict[str, Any],
    intermediates: List[Dict[str, Any]],
    travel_mode: str,
) -> Optional[str]:
    if travel_mode == "TRANSIT":
        return None

    settings = get_settings()

    def _loader() -> Optional[str]:
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": require_google_key(),
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline",
        }
        body = {
            "origin": origin,
            "destination": destination,
            "intermediates": intermediates,
            "travelMode": travel_mode,
            "polylineEncoding": "ENCODED_POLYLINE",
            "polylineQuality": "OVERVIEW",
        }
        response = get_session().post(url, headers=headers, data=dumps_bytes(body), timeout=60)
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes") or []
        if not routes:
            return None
        return routes[0].get("polyline", {}).get("encodedPolyline")

    polyline, cache_hit = cached_call(
        prefix="routes.polyline",
        payload={
            "origin": origin,
            "destination": destination,
            "intermediates": intermediates,
            "travel_mode": travel_mode,
        },
        ttl_sec=settings.cache_ttl_polyline_sec,
        loader=_loader,
    )
    METRICS.record_upstream(
        "routes.polyline",
        cost_estimate=settings.estimate_cost_routes_polyline if not cache_hit else 0.0,
        cache_hit=cache_hit,
    )
    return polyline
