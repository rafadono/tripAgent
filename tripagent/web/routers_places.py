from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from tripagent.config import get_settings
from tripagent.google.search import (
    estimate_parking_cost_clp,
    haversine_m,
    nearby_search,
    text_search,
    walk_minutes,
)
from tripagent.web.dependencies import guard_costly_endpoint

router = APIRouter(tags=["places"])

BUS_FARE_CLP = 770
METRO_FARE_CLP = {"offpeak": 710, "valley": 790, "peak": 870}


class SearchReq(BaseModel):
    query: str
    max_results: int = 8


@router.post("/search_places")
def search_places(req: SearchReq, request: Request):
    settings = get_settings()
    guard_costly_endpoint(
        request=request,
        endpoint="search_places",
        limit=settings.rate_limit_search_per_window,
    )
    places = text_search(req.query, max_results=req.max_results)
    out = []
    for p in places:
        loc = p.get("location") or {}
        out.append(
            {
                "place_id": p.get("id"),
                "name": (p.get("displayName") or {}).get("text"),
                "address": p.get("formattedAddress"),
                "lat": loc.get("latitude"),
                "lng": loc.get("longitude"),
            }
        )
    return {"results": out}


class ParkingReq(BaseModel):
    lat: float
    lng: float
    radius_m: float = 600


@router.post("/nearest_parking")
def nearest_parking(req: ParkingReq, request: Request):
    settings = get_settings()
    guard_costly_endpoint(
        request=request,
        endpoint="nearest_parking",
        limit=settings.rate_limit_parking_per_window,
    )

    raw_parking = nearby_search(
        req.lat,
        req.lng,
        included_types=["parking"],
        max_results=5,
        radius_m=req.radius_m,
    )

    parking_out = []
    for p in raw_parking:
        loc = p.get("location") or {}
        plat = loc.get("latitude")
        plng = loc.get("longitude")
        if plat is None or plng is None:
            continue
        dist = haversine_m(req.lat, req.lng, plat, plng)
        cost = estimate_parking_cost_clp(dist)
        parking_out.append(
            {
                "place_id": p.get("id"),
                "name": (p.get("displayName") or {}).get("text", "Estacionamiento"),
                "address": p.get("formattedAddress", ""),
                "lat": plat,
                "lng": plng,
                "distance_m": round(dist),
                "walk_min": walk_minutes(dist),
                "cost_clp_hr": cost["price_clp_hr"],
                "cost_tier": cost["tier"],
            }
        )
    parking_out.sort(key=lambda x: x["distance_m"])

    raw_metro = nearby_search(
        req.lat,
        req.lng,
        included_types=["subway_station", "transit_station"],
        max_results=3,
        radius_m=1200,
    )

    metro_out = []
    for m in raw_metro:
        loc = m.get("location") or {}
        mlat = loc.get("latitude")
        mlng = loc.get("longitude")
        if mlat is None or mlng is None:
            continue
        dist = haversine_m(req.lat, req.lng, mlat, mlng)
        metro_out.append(
            {
                "place_id": m.get("id"),
                "name": (m.get("displayName") or {}).get("text", "Estacion metro"),
                "address": m.get("formattedAddress", ""),
                "lat": mlat,
                "lng": mlng,
                "distance_m": round(dist),
                "walk_min": walk_minutes(dist),
                "cost_clp_trip": METRO_FARE_CLP["valley"],
                "cost_clp_trip_low": METRO_FARE_CLP["offpeak"],
                "cost_clp_trip_high": METRO_FARE_CLP["peak"],
                "cost_tier": "Tarifa metro estimada por viaje",
            }
        )
    metro_out.sort(key=lambda x: x["distance_m"])

    return {
        "parking": parking_out[:3],
        "metro": metro_out[:2],
        "public_transport_fares_clp": {
            "bus_trip": BUS_FARE_CLP,
            "metro_trip_low": METRO_FARE_CLP["offpeak"],
            "metro_trip_valley": METRO_FARE_CLP["valley"],
            "metro_trip_peak": METRO_FARE_CLP["peak"],
        },
    }

