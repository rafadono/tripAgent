from __future__ import annotations

import time
from typing import Any

from tripagent.ab_testing import select_identity, stable_variant
from tripagent.config import AppSettings
from tripagent.persistence import PERSISTENCE


class OpsExperimentsService:
    def ab_assign(
        self,
        settings: AppSettings,
        *,
        experiment: str,
        override_session_id: str | None,
        variants: list[str],
        session_id: str | None,
        user_id: str | None,
    ) -> dict[str, Any]:
        if not settings.ab_test_enabled:
            return {"enabled": False, "variant": None}
        identity = select_identity(session_id=session_id, user_id=user_id, override=override_session_id)
        variant = stable_variant(experiment, identity, variants)
        objective = variant if variant in {"time", "money", "comfort"} else None
        PERSISTENCE.record_ab_event(
            session_id=session_id or override_session_id,
            user_id=user_id,
            experiment=experiment,
            variant=variant,
            objective=objective,
            event_type="exposure",
            value=0.0,
            meta={"identity_source": "session_or_user"},
        )
        return {"enabled": True, "experiment": experiment, "variant": variant}

    def ab_track(
        self,
        settings: AppSettings,
        *,
        experiment: str,
        variant: str,
        objective: str | None,
        event_type: str,
        value: float,
        session_id: str | None,
        user_id: str | None,
        override_session_id: str | None = None,
    ) -> dict[str, Any]:
        if not settings.ab_test_enabled:
            return {"enabled": False}
        PERSISTENCE.record_ab_event(
            session_id=session_id or override_session_id,
            user_id=user_id,
            experiment=experiment,
            variant=variant,
            objective=objective,
            event_type=event_type,
            value=value,
            meta={},
        )
        return {"ok": True}

    def ab_report(self, *, experiment: str, since_days: int) -> dict[str, Any]:
        now = int(time.time())
        since = now - max(1, min(365, since_days)) * 86_400
        return PERSISTENCE.ab_report(experiment=experiment, since_unix=since)
