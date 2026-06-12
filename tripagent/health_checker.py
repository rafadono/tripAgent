import os
import time
import requests
from pydantic import BaseModel
from tripagent.http_client import get_session

class ComponentCheck(BaseModel):
    status: str                          # "pass" | "warn" | "fail"
    time_ms: float | None = None         # verification latency
    output: str | None = None            # error message if it fails

def check_api_key() -> ComponentCheck:
    """Verifies that the GOOGLE_MAPS_API_KEY environment variable exists and is not empty."""
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not key:
        return ComponentCheck(status="fail", output="GOOGLE_MAPS_API_KEY is not configured")
    if len(key) < 20:
        return ComponentCheck(status="warn", output="GOOGLE_MAPS_API_KEY appears invalid (too short)")
    return ComponentCheck(status="pass")

def check_google_places() -> ComponentCheck:
    """
    Makes a minimal call to Places Text Search to verify connectivity
    and API key permissions. Uses a trivial single-result query.
    """
    try:
        key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if not key:
            return ComponentCheck(status="fail", output="No API key provided, unable to verify")

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "places.id",
        }
        t0 = time.perf_counter()
        r = get_session().post(
            url,
            headers=headers,
            json={"textQuery": "test", "pageSize": 1},
            timeout=5,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

        if r.status_code == 200:
            return ComponentCheck(status="pass", time_ms=elapsed_ms)
        if r.status_code == 401:
            return ComponentCheck(
                status="fail", time_ms=elapsed_ms,
                output="Invalid API key or insufficient permissions (HTTP 401)"
            )
        if r.status_code == 403:
            return ComponentCheck(
                status="fail", time_ms=elapsed_ms,
                output="Places API not enabled in this Google Cloud project (HTTP 403)"
            )
        return ComponentCheck(
            status="warn", time_ms=elapsed_ms,
            output=f"Unexpected response from Google Places: HTTP {r.status_code}"
        )

    except requests.Timeout:
        return ComponentCheck(status="warn", output="Google Places API did not respond in 5s (timeout)")
    except requests.ConnectionError:
        return ComponentCheck(status="fail", output="No connectivity to Google Places API")
    except Exception as e:
        return ComponentCheck(status="fail", output=f"Unexpected error: {e}")

def check_google_routes() -> ComponentCheck:
    """
    Verifies connectivity with Routes API using a minimal 2-point call.
    """
    try:
        key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if not key:
            return ComponentCheck(status="fail", output="No API key provided, unable to verify")

        url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "originIndex,destinationIndex,duration",
        }
        # 2 points in Santiago for a minimal 2x2 matrix
        body = {
            "origins":      [{"waypoint": {"location": {"latLng": {"latitude": -33.45, "longitude": -70.65}}}}],
            "destinations": [{"waypoint": {"location": {"latLng": {"latitude": -33.46, "longitude": -70.66}}}}],
            "travelMode": "DRIVE",
        }
        t0 = time.perf_counter()
        r = get_session().post(url, headers=headers, json=body, timeout=5)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

        if r.status_code == 200:
            return ComponentCheck(status="pass", time_ms=elapsed_ms)
        if r.status_code in (401, 403):
            return ComponentCheck(
                status="fail", time_ms=elapsed_ms,
                output=f"Routes API access denied (HTTP {r.status_code}) — verify that it is enabled"
            )
        return ComponentCheck(
            status="warn", time_ms=elapsed_ms,
            output=f"Unexpected response from Routes API: HTTP {r.status_code}"
        )

    except requests.Timeout:
        return ComponentCheck(status="warn", output="Routes API did not respond in 5s (timeout)")
    except requests.ConnectionError:
        return ComponentCheck(status="fail", output="No connectivity to Routes API")
    except Exception as e:
        return ComponentCheck(status="fail", output=f"Unexpected error: {e}")