from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import HTTPException, Request

from tripagent.config import AppSettings
from tripagent.monetization import user_daily_quota_limit
from tripagent.monetization import user_tier
from tripagent.persistence import PERSISTENCE
from tripagent.security import extract_bearer_or_user_token


def _users_map(settings: AppSettings) -> dict[str, str]:
    users: dict[str, str] = {}
    for item in settings.auth_users:
        if ":" not in item:
            continue
        username, password = item.split(":", 1)
        username = username.strip()
        if username:
            users[username] = password
    return users


def login_user(settings: AppSettings, username: str, password: str) -> dict[str, Any]:
    users = _users_map(settings)
    if username not in users or users[username] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + max(300, settings.session_ttl_sec)
    PERSISTENCE.ensure_user_plan(username)
    PERSISTENCE.save_session(token, username, expires_at)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "username": username,
        "plan_tier": user_tier(settings, username),
    }


def require_authenticated_user(request: Request, settings: AppSettings) -> str:
    if not settings.auth_enabled:
        return "anonymous"
    token = extract_bearer_or_user_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    session = PERSISTENCE.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return str(session["username"])


def enforce_daily_plan_quota(settings: AppSettings, username: str) -> tuple[int, int]:
    limit = user_daily_quota_limit(settings, username)
    allowed, used = PERSISTENCE.try_increment_daily_quota(username, limit)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily plan quota exceeded ({limit}/day)",
        )
    return used, limit


def rollback_daily_plan_quota(username: str) -> None:
    PERSISTENCE.decrement_daily_quota(username)
