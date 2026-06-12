from __future__ import annotations

from fastapi import Request

from tripagent.persistence import PERSISTENCE


def extract_bearer_or_user_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    return request.headers.get("X-User-Token", "").strip()


def extract_session_id(request: Request) -> str | None:
    return request.cookies.get("tripagent_session_id") or request.headers.get("X-Session-Id")


def resolve_session_user(request: Request) -> str | None:
    token = extract_bearer_or_user_token(request)
    if not token:
        return None
    session = PERSISTENCE.get_session(token)
    if not session:
        return None
    return str(session.get("username"))
