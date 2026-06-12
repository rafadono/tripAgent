from datetime import date as date_type, datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Mode = Literal["walking", "driving", "transit", "cycling"]
Objective = Literal["time", "money", "comfort", "google_route_opt"]
WaypointType = Literal["parking", "metro", "bus", "other"]


class LocationIn(BaseModel):
    model_config = ConfigDict(frozen=False)
    place_id: Optional[str] = None
    query:    Optional[str] = None
    lat:      Optional[float] = None
    lng:      Optional[float] = None


class POIIn(BaseModel):
    model_config = ConfigDict(frozen=False)
    place_id:      Optional[str]          = None
    query:         Optional[str]          = None
    duration_min:  Optional[int]          = None
    open_time:     Optional[str]          = None
    close_time:    Optional[str]          = None
    arrival_mode:  Optional[Mode]         = None        # mode for the leg arriving here
    is_waypoint:   bool                   = False       # technical stop: duration 0, mandatory
    waypoint_type: Optional[WaypointType] = None        # parking | metro | bus | other


class DayIn(BaseModel):
    date:                 str
    day_start_time:       str
    day_end_time:         str
    start_location:       LocationIn
    start_is_optimizable: bool = False
    pois:                 List[POIIn]

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            date_type.fromisoformat(v)
        except ValueError as exc:
            raise ValueError("date must use format YYYY-MM-DD") from exc
        return v

    @field_validator("day_start_time", "day_end_time")
    @classmethod
    def validate_hhmm(cls, v: str) -> str:
        if len(v) != 5:
            raise ValueError("time must use format HH:MM")
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError as exc:
            raise ValueError("time must use format HH:MM (24h)") from exc
        return v


class PlanRequest(BaseModel):
    days:      List[DayIn]
    mode:      Mode      = "driving"
    objective: Objective = "time"


class StopOut(BaseModel):
    place_id:             str
    name:                 Optional[str]          = None
    lat:                  Optional[float]        = None
    lng:                  Optional[float]        = None
    arrival:              str
    depart:               str
    travel_min_from_prev: int
    wait_min:             int
    visit_min:            int
    window_open:          Optional[str]          = None
    window_close:         Optional[str]          = None
    leg_mode:             Optional[Mode]         = None  # mode used to arrive here
    is_waypoint:          bool                   = False
    waypoint_type:        Optional[WaypointType] = None


class DayPlanOut(BaseModel):
    date:             str
    stops:            List[StopOut]
    total_travel_min: int
    total_wait_min:   int
    total_visit_min:  int
    map_html_path:    Optional[str] = None
    encoded_polyline: Optional[str] = None
    quality_warnings: List[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    mode:      Mode
    objective: Objective
    days:      List[DayPlanOut]


class ReplanRequest(BaseModel):
    base_request: PlanRequest
    delay_min: int = 0
    removed_place_ids: List[str] = Field(default_factory=list)
    reason: Optional[str] = None


class ReplanResponse(BaseModel):
    mode:      Mode
    objective: Objective
    days:      List[DayPlanOut]
    replan_reason: Optional[str] = None
    applied_delay_min: int = 0
    removed_place_ids: List[str] = Field(default_factory=list)


class RankedAlternative(BaseModel):
    objective: Objective
    score: float
    total_travel_min: int
    total_wait_min: int
    total_visit_min: int
    rationale: str


class AlternativesResponse(BaseModel):
    ranking: List[RankedAlternative]
