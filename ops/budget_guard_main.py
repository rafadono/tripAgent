"""
Sample Cloud Run function entrypoint for budget notifications.

Flow:
Cloud Billing Budget Alert -> Pub/Sub -> Cloud Run function -> POST /ops/cost-guard
"""
from __future__ import annotations

import base64
import os
from typing import Any

from tripagent.http_client import get_session
from tripagent.jsonx import loads


TRIPAGENT_OPS_URL = os.getenv("TRIPAGENT_OPS_URL", "").rstrip("/")
TRIPAGENT_ADMIN_TOKEN = os.getenv("TRIPAGENT_ADMIN_TOKEN", "")
BUDGET_COST_THRESHOLD = float(os.getenv("BUDGET_COST_THRESHOLD", "0"))


def _decode_pubsub_envelope(cloud_event_data: dict[str, Any]) -> dict[str, Any]:
    message = (cloud_event_data or {}).get("message", {})
    encoded = message.get("data")
    if not encoded:
        return {}
    payload = base64.b64decode(encoded).decode("utf-8")
    try:
        return loads(payload)
    except Exception:
        return {}


def _extract_cost_amount(data: dict[str, Any]) -> float:
    # Supports common budget notification fields.
    if "costAmount" in data:
        return float(data["costAmount"])
    amount = ((data.get("costAmountAsDecimal") or {}).get("value")) if isinstance(
        data.get("costAmountAsDecimal"), dict
    ) else None
    if amount is not None:
        return float(amount)
    return 0.0


def budget_guard(cloud_event) -> str:
    if not TRIPAGENT_OPS_URL or not TRIPAGENT_ADMIN_TOKEN:
        raise RuntimeError("TRIPAGENT_OPS_URL and TRIPAGENT_ADMIN_TOKEN are required")

    payload = _decode_pubsub_envelope(cloud_event.data)
    current_cost = _extract_cost_amount(payload)
    should_disable = current_cost >= BUDGET_COST_THRESHOLD

    response = get_session().post(
        f"{TRIPAGENT_OPS_URL}/ops/cost-guard",
        headers={"X-Admin-Token": TRIPAGENT_ADMIN_TOKEN},
        json={
            "costly_endpoints_enabled": not should_disable,
            "plan_endpoint_enabled": not should_disable,
        },
        timeout=10,
    )
    response.raise_for_status()
    return f"cost={current_cost}, disabled={should_disable}"
