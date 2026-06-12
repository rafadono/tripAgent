from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Set

from dateutil import tz

from tripagent.models import (
    AlternativesResponse,
    DayIn,
    DayPlanOut,
    Mode,
    Objective,
    PlanRequest,
    PlanResponse,
    RankedAlternative,
)
from tripagent.google.places import place_details, place_details_many
from tripagent.google.routes import compute_route_matrix, compute_polyline
from tripagent.google.search import resolve_place_id
from tripagent.planner.duration import estimate_visit_duration_min
from tripagent.planner.opening_hours import parse_hhmm, opening_window_for_date
from tripagent.planner.matrix import build_matrices
from tripagent.planner.solver_ortools import Node, solve_day_ortools
from tripagent.planner.schedule import build_schedule
from tripagent.render.map_render import save_map_html

_TRAVEL_MODE_MAP = {
    "driving":  "DRIVE",
    "walking":  "WALK",
    "transit":  "TRANSIT",
    "cycling":  "BICYCLE",
}


def _wp_latlng(lat: float, lng: float) -> Dict[str, Any]:
    return {"location": {"latLng": {"latitude": lat, "longitude": lng}}}


def _quality_warnings(stops: list[Any], total_travel: int, total_wait: int, total_visit: int) -> list[str]:
    warnings: list[str] = []
    if not stops:
        warnings.append("Itinerary with no stops.")
        return warnings
    if total_travel <= 0:
        warnings.append("Total travel time is not positive.")
    if total_visit <= 0:
        warnings.append("Total visit time is not positive.")
    if total_wait > (total_travel + total_visit):
        warnings.append("Excessive waiting time compared to useful itinerary time.")

    seen: set[str] = set()
    for idx, stop in enumerate(stops, start=1):
        pid = str(getattr(stop, "place_id", ""))
        if pid in seen and pid != "DEPOT":
            warnings.append(f"Duplicate POI in route: {pid}")
            break
        seen.add(pid)
        arrival = getattr(stop, "arrival", "")
        depart = getattr(stop, "depart", "")
        if arrival and depart and depart < arrival:
            warnings.append(f"Departure before arrival at stop {idx}.")
            break
    return warnings


def _ensure_place_id_for_start(day: DayIn) -> None:
    loc = day.start_location
    if getattr(loc, "query", None) and not loc.place_id:
        loc.place_id = resolve_place_id(loc.query)
    if not loc.place_id and (loc.lat is None or loc.lng is None):
        raise ValueError("start_location must include place_id, query, or lat+lng")


def _ensure_place_id_for_pois(day: DayIn) -> None:
    for p in day.pois:
        if getattr(p, "query", None) and not p.place_id:
            p.place_id = resolve_place_id(p.query)
        if not p.place_id:
            raise ValueError("Each POI must include place_id or query")


def _compute_matrices_multimodal(
    wps: List[Dict[str, Any]],
    nodes: List[Node],
    global_mode: Mode,
    day_start: datetime,
) -> tuple:
    n = len(nodes)
    modes_needed: Set[Mode] = {global_mode}
    for node in nodes:
        if node.arrival_mode and node.arrival_mode != global_mode:
            modes_needed.add(node.arrival_mode)

    matrices: Dict[Mode, tuple] = {}
    for mode in modes_needed:
        travel_mode = _TRAVEL_MODE_MAP[mode]
        dep_ts = int(day_start.timestamp()) if travel_mode == "TRANSIT" else None
        elements = compute_route_matrix(wps, wps, travel_mode=travel_mode, departure_time=dep_ts)
        dur_m, dist_m_ = build_matrices(elements, n=n)
        matrices[mode] = (dur_m, dist_m_)

    dur_sec, dist_m = matrices[global_mode]

    for j, node in enumerate(nodes):
        if node.arrival_mode and node.arrival_mode != global_mode and node.arrival_mode in matrices:
            mode_dur, mode_dist = matrices[node.arrival_mode]
            for i in range(n):
                dur_sec[i][j] = mode_dur[i][j]
                dist_m[i][j]  = mode_dist[i][j]

    return dur_sec, dist_m


def plan_one_day(day: DayIn, mode: Mode, objective: str, out_dir: str, map_suffix: str = "") -> DayPlanOut:
    d = date.fromisoformat(day.date)

    _ensure_place_id_for_start(day)
    _ensure_place_id_for_pois(day)

    if day.start_location.place_id:
        sp = place_details(day.start_location.place_id, "id,displayName,location,timeZone")
        s_lat   = sp["location"]["latitude"]
        s_lng   = sp["location"]["longitude"]
        s_name  = (sp.get("displayName") or {}).get("text") or "Start"
        tz_name = (sp.get("timeZone") or {}).get("id") or (sp.get("timeZone") or {}).get("name")
    else:
        s_lat   = day.start_location.lat
        s_lng   = day.start_location.lng
        s_name  = "Start"
        tz_name = None

    tzinfo    = tz.gettz(tz_name) if tz_name else tz.tzlocal()
    day_start = datetime.combine(d, parse_hhmm(day.day_start_time)).replace(tzinfo=tzinfo)
    day_end   = datetime.combine(d, parse_hhmm(day.day_end_time)).replace(tzinfo=tzinfo)
    if day_end <= day_start:
        day_end += timedelta(days=1)

    places: Dict[str, Dict[str, Any]] = {}
    detail_ids = [p.place_id for p in day.pois if not p.is_waypoint and p.place_id]
    if detail_ids:
        places = place_details_many(
            detail_ids,
            "id,displayName,location,timeZone,types,regularOpeningHours,currentOpeningHours",
            max_concurrency=8,
        )

    nodes: List[Node] = []
    nodes.append(Node(
        place_id="DEPOT", name=s_name,
        lat=s_lat, lng=s_lng,
        visit_min=0, window=None,
    ))

    if day.start_is_optimizable and day.start_location.place_id:
        nodes.append(Node(
            place_id=day.start_location.place_id,
            name=s_name, lat=s_lat, lng=s_lng,
            visit_min=0, window=(day_start, day_end),
        ))

    for p in day.pois:
        if p.is_waypoint:
            wp = place_details(p.place_id, "id,displayName,location")
            nodes.append(Node(
                place_id=p.place_id,
                name=(wp.get("displayName") or {}).get("text") or p.place_id,
                lat=wp["location"]["latitude"],
                lng=wp["location"]["longitude"],
                visit_min=0,
                window=(day_start, day_end),
                arrival_mode=p.arrival_mode,
                is_waypoint=True,
                waypoint_type=p.waypoint_type,
            ))
        else:
            pl    = places[p.place_id]
            name  = (pl.get("displayName") or {}).get("text") or p.place_id
            lat_  = pl["location"]["latitude"]
            lng_  = pl["location"]["longitude"]
            visit = p.duration_min if p.duration_min is not None else estimate_visit_duration_min(pl)

            result = opening_window_for_date(pl, d, visit, p.open_time, p.close_time)
            if result:
                open_dt, adj_close_dt, raw_close_dt = result
                window        = (open_dt, adj_close_dt)
                raw_win_close = raw_close_dt
            else:
                window        = None
                raw_win_close = None

            nodes.append(Node(
                place_id=p.place_id, name=name,
                lat=lat_, lng=lng_,
                visit_min=visit,
                window=window,
                raw_window_close=raw_win_close,
                arrival_mode=p.arrival_mode,
            ))

    wps = [_wp_latlng(n.lat, n.lng) for n in nodes]
    dur_sec, dist_m = _compute_matrices_multimodal(wps, nodes, mode, day_start)

    if objective == "google_route_opt":
        raise NotImplementedError("objective=google_route_opt requires Route Optimization API.")

    order = solve_day_ortools(nodes, day_start, day_end, dur_sec, dist_m, objective=objective)

    stops, total_travel, total_wait, total_visit = build_schedule(
        nodes, order, day_start, dur_sec
    )
    quality_warnings = _quality_warnings(stops, total_travel, total_wait, total_visit)

    os.makedirs(out_dir, exist_ok=True)
    suffix = f"_{map_suffix}" if map_suffix else ""
    map_path = os.path.join(out_dir, f"map_{day.date}{suffix}.html")

    origin      = _wp_latlng(nodes[0].lat, nodes[0].lng)
    destination = _wp_latlng(nodes[0].lat, nodes[0].lng)
    inter = [
        {"location": {"latLng": {"latitude": nodes[i].lat, "longitude": nodes[i].lng}}}
        for i in order if i != 0
    ]

    poly = None
    if len(inter) <= 25:
        poly = compute_polyline(origin, destination, inter, travel_mode=_TRAVEL_MODE_MAP[mode])

    points = [(nodes[0].lat, nodes[0].lng, "Start")]
    for s in stops:
        n = next(nd for nd in nodes if nd.place_id == s.place_id)
        points.append((n.lat, n.lng, s.name or s.place_id))

    html_path = save_map_html(points, poly, map_path)

    return DayPlanOut(
        date=day.date,
        stops=stops,
        total_travel_min=total_travel,
        total_wait_min=total_wait,
        total_visit_min=total_visit,
        map_html_path=html_path,
        encoded_polyline=poly,
        quality_warnings=quality_warnings,
    )


def plan(req: PlanRequest, out_dir: str = "out", run_id: str | None = None) -> PlanResponse:
    safe_run_id = run_id or uuid.uuid4().hex[:12]
    days_out = [plan_one_day(d, req.mode, req.objective, out_dir, map_suffix=safe_run_id) for d in req.days]
    return PlanResponse(mode=req.mode, objective=req.objective, days=days_out)


def rank_alternatives(req: PlanRequest, out_dir: str = "out") -> AlternativesResponse:
    candidates: list[tuple[Objective, PlanResponse]] = []
    for objective in ("time", "money", "comfort"):
        alt_req = req.model_copy(deep=True)
        alt_req.objective = objective
        candidates.append((objective, plan(alt_req, out_dir=out_dir)))

    ranking: list[RankedAlternative] = []
    for objective, result in candidates:
        day = result.days[0]
        if objective == "time":
            score = float(day.total_travel_min + day.total_wait_min)
            rationale = "Minimizes travel time and wait time."
        elif objective == "money":
            score = float((day.total_travel_min * 0.7) + (day.total_wait_min * 1.2))
            rationale = "Prioritizes lower travel distances/operational costs."
        else:
            score = float((day.total_wait_min * 1.8) + (day.total_travel_min * 0.8))
            rationale = "Reduces fatigue by avoiding long waiting times."
        ranking.append(
            RankedAlternative(
                objective=objective,
                score=round(score, 2),
                total_travel_min=day.total_travel_min,
                total_wait_min=day.total_wait_min,
                total_visit_min=day.total_visit_min,
                rationale=rationale,
            )
        )

    ranking.sort(key=lambda item: item.score)
    return AlternativesResponse(ranking=ranking)
