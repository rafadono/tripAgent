from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from tripagent.models import Objective, Mode, WaypointType


@dataclass
class Node:
    place_id:         str
    name:             str
    lat:              float
    lng:              float
    visit_min:        int
    window:           Optional[Tuple[datetime, datetime]]
    raw_window_close: Optional[datetime] = None
    arrival_mode:     Optional[Mode]     = None   # mode for the leg arriving at this node
    is_waypoint:      bool               = False  # technical stop (duration 0, mandatory)
    waypoint_type:    Optional[WaypointType] = None


def solve_day_ortools(
    nodes: List[Node],
    day_start: datetime,
    day_end: datetime,
    dur_sec: List[List[int]],
    dist_m: List[List[int]],
    objective: Objective,
) -> List[int]:
    n = len(nodes)
    depot = 0
    manager = pywrapcp.RoutingIndexManager(n, 1, depot)
    routing = pywrapcp.RoutingModel(manager)

    def cost_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        if objective == "money":
            return dist_m[i][j]
        return dur_sec[i][j]

    transit_cost = routing.RegisterTransitCallback(cost_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cost)

    service_sec = [nodes[i].visit_min * 60 for i in range(n)]

    def time_cb(from_index: int, to_index: int) -> int:
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return dur_sec[i][j] + service_sec[i]

    transit_time = routing.RegisterTransitCallback(time_cb)

    horizon = int((day_end - day_start).total_seconds())
    routing.AddDimension(transit_time, 6 * 60 * 60, horizon, True, "Time")
    time_dim = routing.GetDimensionOrDie("Time")

    for node_idx in range(n):
        index = manager.NodeToIndex(node_idx)
        if node_idx == depot:
            time_dim.CumulVar(index).SetRange(0, horizon)
            continue
        w = nodes[node_idx].window
        if not w:
            time_dim.CumulVar(index).SetRange(0, horizon)
            continue
        o, c = w
        a = max(0, int((o - day_start).total_seconds()))
        b = min(horizon, int((c - day_start).total_seconds()))
        time_dim.CumulVar(index).SetRange(a, b)

    end_index = routing.End(0)
    time_dim.CumulVar(end_index).SetRange(0, horizon)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 10

    sol = routing.SolveWithParameters(params)
    if not sol:
        raise RuntimeError(
            "No feasible solution found (overly restrictive time windows "
            "or the itinerary does not fit in the day)."
        )

    order: List[int] = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        order.append(manager.IndexToNode(idx))
        idx = sol.Value(routing.NextVar(idx))
    order.append(manager.IndexToNode(idx))
    return order
