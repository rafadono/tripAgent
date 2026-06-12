from __future__ import annotations

import threading

import requests
from requests.adapters import HTTPAdapter

_SESSION: requests.Session | None = None
_LOCK = threading.Lock()


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    with _LOCK:
        if _SESSION is None:
            session = requests.Session()
            adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            _SESSION = session
    return _SESSION
