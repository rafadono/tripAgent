from __future__ import annotations

import json
from typing import Any

try:
    import orjson as _orjson
except Exception:  # pragma: no cover - fallback when optional dep unavailable
    _orjson = None


def dumps_bytes(
    value: Any,
    *,
    sort_keys: bool = False,
    indent: int | None = None,
) -> bytes:
    if _orjson is not None:
        option = 0
        if sort_keys:
            option |= _orjson.OPT_SORT_KEYS
        if indent == 2:
            option |= _orjson.OPT_INDENT_2
        if indent is None or indent == 2:
            return _orjson.dumps(value, option=option)
    return json.dumps(
        value,
        sort_keys=sort_keys,
        ensure_ascii=False,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    ).encode("utf-8")


def dumps_str(
    value: Any,
    *,
    sort_keys: bool = False,
    indent: int | None = None,
) -> str:
    return dumps_bytes(value, sort_keys=sort_keys, indent=indent).decode("utf-8")


def loads(value: str | bytes | bytearray | memoryview) -> Any:
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if _orjson is not None:
        return _orjson.loads(value)
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value)
