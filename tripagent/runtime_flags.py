from __future__ import annotations

import threading
from typing import Any

from tripagent.config import AppSettings


class RuntimeFlags:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._costly_enabled_override: bool | None = None
        self._plan_enabled_override: bool | None = None

    def set_costly_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._costly_enabled_override = enabled

    def set_plan_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._plan_enabled_override = enabled

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "costly_endpoints_enabled_override": self._costly_enabled_override,
                "plan_endpoint_enabled_override": self._plan_enabled_override,
            }

    def costly_enabled(self, settings: AppSettings) -> bool:
        with self._lock:
            if self._costly_enabled_override is not None:
                return self._costly_enabled_override
        return settings.costly_endpoints_enabled

    def plan_enabled(self, settings: AppSettings) -> bool:
        with self._lock:
            if self._plan_enabled_override is not None:
                return self._plan_enabled_override
        return settings.plan_endpoint_enabled


RUNTIME_FLAGS = RuntimeFlags()
