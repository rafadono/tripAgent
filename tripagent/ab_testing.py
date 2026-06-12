from __future__ import annotations

import hashlib


def stable_variant(experiment: str, identity: str, variants: list[str]) -> str:
    digest = hashlib.sha256(f"{experiment}:{identity}".encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % max(1, len(variants))
    return variants[idx] if variants else "time"


def select_identity(session_id: str | None, user_id: str | None, override: str | None = None) -> str:
    return override or session_id or user_id or "anonymous"
