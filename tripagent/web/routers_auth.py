from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from tripagent.auth import login_user, require_authenticated_user
from tripagent.config import get_settings
from tripagent.monetization import monetization_report
from tripagent.monetization import user_daily_quota_limit, user_tier
from tripagent.persistence import PERSISTENCE
from tripagent.web.dependencies import require_admin_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginReq(BaseModel):
    username: str
    password: str


class DevSubscriptionReq(BaseModel):
    username: str
    months: int = 1


@router.post("/login")
def auth_login(req: LoginReq):
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=400, detail="Auth is disabled")
    return login_user(settings, username=req.username.strip(), password=req.password)


@router.get("/me")
def auth_me(request: Request):
    settings = get_settings()
    username = require_authenticated_user(request, settings)
    tier = user_tier(settings, username)
    plan = PERSISTENCE.get_user_plan(username)
    used = PERSISTENCE.get_daily_quota(username)
    return {
        "username": username,
        "plan_tier": tier,
        "subscription_status": plan.get("status"),
        "subscription_renews_at": plan.get("renews_at"),
        "daily_plan_quota": user_daily_quota_limit(settings, username),
        "daily_plan_used": used,
    }


@router.post("/subscribe/dev")
def auth_subscribe_dev(req: DevSubscriptionReq, request: Request):
    require_admin_token(request)
    settings = get_settings()
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")
    months = max(1, min(24, int(req.months)))
    renews_at = int((datetime.now() + timedelta(days=30 * months)).timestamp())
    monthly_price = max(0.0, float(settings.subscription_monthly_price))
    PERSISTENCE.set_user_subscription(
        username=username,
        plan_tier="pro",
        status="active",
        renews_at=renews_at,
        monthly_price=monthly_price,
    )
    if monthly_price > 0:
        PERSISTENCE.record_revenue_event(
            username=username,
            source="subscription",
            amount=monthly_price * months,
            meta={"months": months},
        )
    return {"ok": True, "username": username, "plan_tier": "pro", "renews_at": renews_at}


@router.post("/unsubscribe/dev")
def auth_unsubscribe_dev(req: DevSubscriptionReq, request: Request):
    require_admin_token(request)
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")
    PERSISTENCE.set_user_subscription(
        username=username,
        plan_tier="free",
        status="inactive",
        renews_at=None,
        monthly_price=0.0,
    )
    return {"ok": True, "username": username, "plan_tier": "free"}


@router.get("/monetization/me")
def auth_monetization_me(request: Request):
    settings = get_settings()
    username = require_authenticated_user(request, settings)
    report = monetization_report(settings, days=30)
    report["user"] = {
        "username": username,
        "plan_tier": user_tier(settings, username),
        "daily_quota": user_daily_quota_limit(settings, username),
    }
    return report
