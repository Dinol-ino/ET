from __future__ import annotations

import datetime as dt
from typing import Any


def utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


def now_iso() -> str:
    return utcnow().isoformat()


def parse_datetime(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text.replace("Z", "+00:00")

    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed
