"""The "day" that anchors a daily spread.

Pure core, unit-tested. ``day_key`` returns the current calendar date in the
configured timezone as ``YYYY-MM-DD``. The spread for a (user, day) is fixed:
this string is the cache key, so the interpretation and cards never change
until local midnight in the configured zone.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def day_key(tz_name: str, now: datetime | None = None) -> str:
    """Current local date in ``tz_name`` as ``YYYY-MM-DD``.

    ``now`` (a timezone-aware UTC datetime) is injectable for tests; production
    computes it from ``datetime.now(timezone.utc)`` and converts to the target
    zone — mirroring the sibling bots' TZ handling.
    """
    if now is None:
        now = datetime.now(UTC)
    local = now.astimezone(ZoneInfo(tz_name))
    return local.strftime("%Y-%m-%d")
