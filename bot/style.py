"""Voice of the reading — which persona interprets the cards.

Codes are persisted in ``users.style`` and referenced by i18n labels and the
prompt fragments in ``interpret._STYLE_VOICES``. **Keep them stable**, the same
rule as the product codes in ``pricing``.

The style changes only the *voice*. The product rule underneath it does not
move: every reading still describes the current disposition and still refuses to
predict, in every style (only the paid "future" add-on looks ahead).
"""

from __future__ import annotations

FORTUNE = "fortune"  # the original esoteric reader
PSY = "psy"  # psychoanalytic
LOGIC = "logic"  # impersonal, unemotional analysis
BUDDY = "buddy"  # blunt friend, profanity included

STYLES = (FORTUNE, PSY, LOGIC, BUDDY)  # display order in /settings
DEFAULT = FORTUNE


def normalize(value: str | None) -> str:
    """A stored style, or the default for NULL / anything unrecognised."""
    return value if value in STYLES else DEFAULT
