from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from tripagent.config import AppSettings
from tripagent.persistence import PERSISTENCE


def current_month_ym() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def get_subscription_price(settings: AppSettings) -> float:
    base = float(settings.subscription_monthly_price)
    price = PERSISTENCE.get_current_subscription_price(default=base)
    if price <= 0:
        return max(0.0, base)
    return float(price)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def cashflow_month(settings: AppSettings, month_ym: str) -> dict[str, Any]:
    flow = PERSISTENCE.month_cashflow(month_ym)
    infra_logged = PERSISTENCE.get_infra_cost(month_ym)
    if infra_logged <= 0 and settings.infra_monthly_cost_estimate > 0:
        infra_logged = float(settings.infra_monthly_cost_estimate)
        flow["cost_total"] = float(flow["cost_total"]) + infra_logged
        flow["margin"] = float(flow["revenue_total"]) - float(flow["cost_total"])
        flow["lines"].append({"entry_type": "cost", "category": "infra_estimate", "amount": infra_logged})
    tiers = PERSISTENCE.count_user_tiers()
    flow["tiers"] = tiers
    flow["current_subscription_price"] = round(get_subscription_price(settings), 6)
    return flow


def recommend_subscription_price(settings: AppSettings, month_ym: str) -> dict[str, Any]:
    flow = cashflow_month(settings, month_ym)
    revenue_total = float(flow["revenue_total"])
    cost_total = float(flow["cost_total"])
    current_price = float(flow["current_subscription_price"])
    pro_users = max(1, int(flow.get("tiers", {}).get("pro", 0)))
    target_margin = float(settings.monetization_target_margin)
    target_revenue = cost_total * (1.0 + target_margin)
    shortfall = max(0.0, target_revenue - revenue_total)

    if shortfall <= 0:
        desired_price = current_price * (1.0 - (settings.max_price_change_pct * 0.25))
    else:
        desired_price = current_price + (shortfall / pro_users)

    max_delta = max(0.0, float(settings.max_price_change_pct))
    lower_step = current_price * (1.0 - max_delta)
    upper_step = current_price * (1.0 + max_delta)
    if current_price <= 0:
        lower_step = 0.0
        upper_step = max(0.0, float(settings.subscription_price_max))
    stepped_price = _clamp(desired_price, lower_step, upper_step)
    bounded_price = _clamp(
        stepped_price,
        float(settings.subscription_price_min),
        float(settings.subscription_price_max),
    )
    recommendation = {
        "month_ym": month_ym,
        "current_price": round(current_price, 6),
        "recommended_price": round(bounded_price, 6),
        "shortfall": round(shortfall, 6),
        "target_revenue": round(target_revenue, 6),
        "target_margin_rate": round(target_margin, 4),
        "pro_users": int(pro_users),
        "notes": (
            "Price decrease candidate (project already above target)." if shortfall <= 0
            else "Price increase candidate to reach target margin."
        ),
    }
    return recommendation


def reconcile_month(settings: AppSettings, month_ym: str, apply_price: bool) -> dict[str, Any]:
    flow = cashflow_month(settings, month_ym)
    rec = recommend_subscription_price(settings, month_ym)
    applied = False
    if apply_price:
        PERSISTENCE.set_current_subscription_price(
            value=float(rec["recommended_price"]),
            reason=f"monthly_reconcile:{month_ym}",
            meta={
                "revenue_total": flow["revenue_total"],
                "cost_total": flow["cost_total"],
                "margin": flow["margin"],
            },
        )
        applied = True

    PERSISTENCE.record_finance_reconcile(
        month_ym=month_ym,
        revenue_total=float(flow["revenue_total"]),
        cost_total=float(flow["cost_total"]),
        margin=float(flow["margin"]),
        recommended_price=float(rec["recommended_price"]),
        applied=applied,
        meta={"recommendation": rec, "flow": flow},
    )
    return {
        "flow": flow,
        "recommendation": rec,
        "applied": applied,
    }


def feasibility_summary(settings: AppSettings) -> dict[str, Any]:
    month = current_month_ym()
    flow = cashflow_month(settings, month)
    rec = recommend_subscription_price(settings, month)
    req_revenue = max(0.0, float(flow["cost_total"]))
    tiers = flow.get("tiers", {})
    free_users = int(tiers.get("free", 0))
    pro_users = int(tiers.get("pro", 0))
    conversion = (pro_users / max(1, free_users + pro_users))
    affordable = rec["recommended_price"] <= (float(settings.subscription_price_max) * 0.6)
    return {
        "month_ym": month,
        "cashflow": flow,
        "recommended_price": rec["recommended_price"],
        "required_monthly_revenue_for_breakeven": round(req_revenue, 6),
        "current_conversion_rate": round(conversion, 4),
        "target_conversion_rate": round(float(settings.target_conversion_rate), 4),
        "affordability_flag": affordable,
        "sustainable_now": float(flow["margin"]) >= 0,
    }


def annual_cashflow(settings: AppSettings, year: int, scope: str = "calendar") -> dict[str, Any]:
    y = max(2000, min(2100, int(year)))
    all_months = PERSISTENCE.ledger_months()
    months = [f"{y}-{m:02d}" for m in range(1, 13)]
    if scope == "from_start":
        same_year = [m for m in all_months if m.startswith(f"{y}-")]
        if same_year:
            first = min(same_year)
            months = [m for m in months if m >= first]
    month_rows = []
    total_rev = 0.0
    total_cost = 0.0
    for month in months:
        flow = cashflow_month(settings, month)
        total_rev += float(flow["revenue_total"])
        total_cost += float(flow["cost_total"])
        month_rows.append(
            {
                "month_ym": month,
                "revenue_total": round(float(flow["revenue_total"]), 6),
                "cost_total": round(float(flow["cost_total"]), 6),
                "margin": round(float(flow["margin"]), 6),
            }
        )
    margin = total_rev - total_cost
    margin_rate = (margin / total_rev) if total_rev > 0 else 0.0
    return {
        "year": y,
        "scope": scope,
        "months": month_rows,
        "totals": {
            "revenue_total": round(total_rev, 6),
            "cost_total": round(total_cost, 6),
            "margin": round(margin, 6),
            "margin_rate": round(margin_rate, 4),
        },
    }
