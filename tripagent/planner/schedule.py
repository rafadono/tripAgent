import math
from datetime import datetime, timedelta
from typing import List, Tuple

from tripagent.models import StopOut
from tripagent.planner.solver_ortools import Node


def build_schedule(
    nodes: List[Node],
    order: List[int],
    day_start: datetime,
    dur_sec: List[List[int]],
) -> Tuple[List[StopOut], int, int, int]:
    t = day_start
    total_travel = total_wait = total_visit = 0
    stops: List[StopOut] = []

    for k in range(1, len(order)):
        prev = order[k - 1]
        cur  = order[k]

        travel_min = int(math.ceil(dur_sec[prev][cur] / 60))
        t += timedelta(minutes=travel_min)
        total_travel += travel_min

        if cur == 0:
            continue

        node = nodes[cur]
        wait = 0
        if node.window:
            o, c = node.window
            if t < o:
                wait = int((o - t).total_seconds() // 60)
                t = o
            if t > c:
                raise RuntimeError(f"Late for window at {node.name}")

        arrival = t
        depart  = t + timedelta(minutes=node.visit_min)
        total_wait  += wait
        total_visit += node.visit_min

        stops.append(StopOut(
            place_id             = node.place_id,
            name                 = node.name,
            lat                  = node.lat,
            lng                  = node.lng,
            arrival              = arrival.isoformat(),
            depart               = depart.isoformat(),
            travel_min_from_prev = travel_min,
            wait_min             = wait,
            visit_min            = node.visit_min,
            window_open          = node.window[0].isoformat() if node.window else None,
            window_close         = (node.raw_window_close or node.window[1]).isoformat()
                                   if node.window else None,
            leg_mode             = node.arrival_mode,
            is_waypoint          = node.is_waypoint,
            waypoint_type        = node.waypoint_type,
        ))

        t = depart

    return stops, total_travel, total_wait, total_visit
