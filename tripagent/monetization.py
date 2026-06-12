from __future__ import annotations

from datetime import datetime
from typing import Any

from tripagent.config import AppSettings
from tripagent.persistence import PERSISTENCE


def user_tier(settings: AppSettings, username: str) -> str:
    plan = PERSISTENCE.get_user_plan(username)
    tier = str(plan.get("plan_tier", "free")).lower()
    status = str(plan.get("status", "inactive")).lower()
    renews_at = plan.get("renews_at")
    now = int(datetime.now().timestamp())
    if tier == "pro" and status == "active" and (renews_at is None or int(renews_at) > now):
        return "pro"
    return "free"


def user_daily_quota_limit(settings: AppSettings, username: str) -> int:
    tier = user_tier(settings, username)
    if tier == "pro":
        return max(1, settings.pro_daily_quota_per_user)
    return max(1, settings.free_daily_quota_per_user or settings.plan_daily_quota_per_user)


def monetization_report(settings: AppSettings, days: int = 30) -> dict[str, Any]:
    window_days = max(1, min(365, int(days)))
    now = datetime.now()
    since = datetime(now.year, now.month, now.day).timestamp() - ((window_days - 1) * 86_400)
    business = PERSISTENCE.business_snapshot_since(int(since))
    revenue = PERSISTENCE.revenue_snapshot_since(int(since))
    api_cost = float(business.get("totals", {}).get("api_cost", 0.0))
    ads_rev = float(business.get("totals", {}).get("ads_revenue", 0.0))
    subs_rev = float(revenue.get("totals", {}).get("amount", 0.0))
    total_rev = ads_rev + subs_rev
    margin = total_rev - api_cost
    margin_rate = (margin / total_rev) if total_rev > 0 else 0.0
    target = float(settings.monetization_target_margin)
    sustainable = total_rev >= api_cost and margin_rate >= target
    recommendation = (
        "Sustainable mode: keep growth."
        if sustainable
        else "Not sustainable yet: increase subscription conversion and reduce costly usage."
    )
    return {
        "window_days": window_days,
        "api_cost": round(api_cost, 6),
        "ads_revenue": round(ads_rev, 6),
        "subscription_revenue": round(subs_rev, 6),
        "total_revenue": round(total_rev, 6),
        "margin": round(margin, 6),
        "margin_rate": round(margin_rate, 4),
        "target_margin_rate": round(target, 4),
        "sustainable": sustainable,
        "recommendation": recommendation,
        "inputs": {
            "free_quota_per_day": settings.free_daily_quota_per_user,
            "pro_quota_per_day": settings.pro_daily_quota_per_user,
            "subscription_monthly_price": settings.subscription_monthly_price,
            "ads_revenue_per_request": settings.est_ads_revenue_per_request,
        },
    }
