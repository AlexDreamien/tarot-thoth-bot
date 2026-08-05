"""Premium subscription state.

Pure core — no clock: "today" is passed in as a day-key (``daily.day_key``), the
same convention as ``memory``, so the rules are deterministic and testable.

``users.premium_until`` holds a ``YYYY-MM-DD`` date and premium is active
*through* that day inclusive. The format is the same sortable day-key used for
``spreads.day``, so "is it still valid" is a string comparison.

Nothing is gated on this yet — the paid packages come later. The flag exists so
the state is already being recorded when they do.
"""

from __future__ import annotations

from datetime import date

# Everyone who was already using the bot when premium landed is grandfathered in
# (see the one-time backfill in ``db._migrate``). Far enough out to mean
# "indefinitely" without needing a NULL-means-forever special case.
GRANDFATHER_UNTIL = "2099-01-01"


def normalize(value: str | None) -> str | None:
    """A stored expiry date, or None for anything that isn't one."""
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def is_active(premium_until: str | None, today: str) -> bool:
    """Is premium valid on ``today``? Inclusive of the expiry day itself."""
    until = normalize(premium_until)
    return bool(until) and today <= until
