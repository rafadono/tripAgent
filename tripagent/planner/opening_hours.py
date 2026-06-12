from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional, Tuple
from dateutil import tz


def parse_hhmm(s: str) -> time:
    hh, mm = s.split(":")
    return time(int(hh), int(mm))


def _combine_local(d: date, t: time, tzinfo) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=tzinfo)


def opening_window_for_date(
    place: Dict[str, Any],
    target_date: date,
    visit_min: int,
    override_open: Optional[str] = None,
    override_close: Optional[str] = None,
) -> Optional[Tuple[datetime, datetime, datetime]]:
    """
    Returns (open_dt, adj_close_dt, raw_close_dt) where:
      - open_dt       : actual opening time of the place
      - adj_close_dt  : latest valid time to START the visit (close - visit_min)
      - raw_close_dt  : actual closing time of the place (to show the user in the itinerary)

    Returns None if there is no opening hours information.
    """
    tz_name = (place.get("timeZone") or {}).get("id") or (place.get("timeZone") or {}).get("name")
    tzinfo = tz.gettz(tz_name) if tz_name else tz.tzlocal()

    if override_open and override_close:
        o = _combine_local(target_date, parse_hhmm(override_open), tzinfo)
        c = _combine_local(target_date, parse_hhmm(override_close), tzinfo)
        if c <= o:
            c += timedelta(days=1)
        adj = c - timedelta(minutes=visit_min)
        return (o, adj, c) if adj > o else None

    oh = place.get("regularOpeningHours") or place.get("currentOpeningHours")
    if not oh:
        return None

    periods = oh.get("periods") or []
    # Conversion: Python weekday() Mon=0..Sun=6 → API: Sun=0..Sat=6
    dow = (target_date.weekday() + 1) % 7

    candidates = []
    for p in periods:
        op = p.get("open", {})
        cl = p.get("close", {})
        if op.get("day") is None or int(op["day"]) != dow:
            continue
        ohh = int(op.get("hour", 0))
        omm = int(op.get("minute", 0))
        if not cl:
            # Open 24/7
            o = _combine_local(target_date, time(0, 0), tzinfo)
            c = _combine_local(target_date, time(23, 59), tzinfo)
            adj = c - timedelta(minutes=visit_min)
            return (o, adj, c) if adj > o else None
        chh = int(cl.get("hour", 0))
        cmm = int(cl.get("minute", 0))
        candidates.append((ohh * 60 + omm, chh * 60 + cmm))

    if not candidates:
        return None

    # If there are multiple periods, take the widest range of the day
    start_min = min(s for s, _ in candidates)
    end_min   = max(e for _, e in candidates)

    o = _combine_local(target_date, time(start_min // 60, start_min % 60), tzinfo)
    c = _combine_local(target_date, time(end_min   // 60, end_min   % 60), tzinfo)
    if c <= o:
        c += timedelta(days=1)

    adj = c - timedelta(minutes=visit_min)
    return (o, adj, c) if adj > o else None
