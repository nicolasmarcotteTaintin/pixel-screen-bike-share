"""Quiet-hours scheduling: when should the panel be turned off?

The window is configured with two ``"HH:MM"`` strings and may wrap past
midnight (e.g. ``21:00`` → ``08:00``). An empty/invalid pair disables it.
"""

from __future__ import annotations

import time
from typing import Any

from .sun import montreal_sunset_minutes


def _parse_minutes(value: Any) -> int | None:
    try:
        hours, minutes = str(value).strip().split(":")
        total = int(hours) * 60 + int(minutes)
    except (ValueError, AttributeError):
        return None
    return total if 0 <= total < 24 * 60 else None


def is_off_now(config: dict[str, Any], now: time.struct_time | None = None) -> bool:
    """True if the current local time falls in the configured off-window.

    ``off_start`` may be the literal ``"sunset"`` to follow Montréal's sunset.
    """
    if not config.get("off_enabled", True):
        return False
    now = now or time.localtime()

    if str(config.get("off_start", "")).strip().lower() == "sunset":
        start = montreal_sunset_minutes(now)
    else:
        start = _parse_minutes(config.get("off_start", ""))
    end = _parse_minutes(config.get("off_end", ""))
    if start is None or end is None or start == end:
        return False

    minute_of_day = now.tm_hour * 60 + now.tm_min
    if start < end:
        return start <= minute_of_day < end
    # Window wraps past midnight (e.g. 21:00 -> 08:00).
    return minute_of_day >= start or minute_of_day < end
