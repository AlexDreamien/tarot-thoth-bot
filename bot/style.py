"""How the bot speaks to a querent: the voice it uses, and how it addresses them.

Codes are persisted in ``users.style`` / ``users.gender`` and referenced by i18n
labels and the prompt fragments in ``bot/interpret.py``. **Keep them stable**,
the same rule as the product codes in ``pricing``.

None of this moves the product rule underneath: every reading still describes
the current disposition and still refuses to predict, in every voice (only the
paid "future" add-on looks ahead).
"""

from __future__ import annotations

from dataclasses import dataclass

# --- voice ---------------------------------------------------------------

FORTUNE = "fortune"  # the original esoteric reader
PSY = "psy"  # psychoanalytic
LOGIC = "logic"  # impersonal, unemotional analysis
BUDDY = "buddy"  # blunt friend, profanity included

STYLES = (FORTUNE, PSY, LOGIC, BUDDY)  # display order in /settings
DEFAULT = FORTUNE


def normalize(value: str | None) -> str:
    """A stored style, or the default for NULL / anything unrecognised."""
    return value if value in STYLES else DEFAULT


# --- address -------------------------------------------------------------

MALE = "m"
FEMALE = "f"
GENDERS = (MALE, FEMALE)

# The name is interpolated into the system prompt, so it is kept short and
# single-line: a "name" is not a place to smuggle instructions from.
MAX_NAME = 32


def normalize_gender(value: str | None) -> str | None:
    """A stored gender, or None — which means *unknown*, not "default to male".
    Readings then avoid gendered agreement altogether."""
    return value if value in GENDERS else None


def clean_name(raw: str | None) -> str | None:
    """Sanitise a self-chosen name for use in a prompt: one line, trimmed,
    length-capped. None if nothing usable is left."""
    if not raw:
        return None
    flat = " ".join(raw.split())  # collapses newlines and runs of whitespace
    flat = flat.replace("«", "").replace("»", "").strip()
    return flat[:MAX_NAME] or None


@dataclass(frozen=True)
class Persona:
    """Everything the model is told about *who it is talking to and how*."""

    style: str = DEFAULT
    gender: str | None = None  # None == unknown, write genderless
    name: str | None = None  # None == no name, address them directly

    @classmethod
    def from_row(cls, row) -> Persona:
        """Build from a ``users`` row (or None, for a user we've never stored)."""
        if row is None:
            return cls()
        return cls(
            style=normalize(_cell(row, "style")),
            gender=normalize_gender(_cell(row, "gender")),
            name=clean_name(_cell(row, "display_name")),
        )


def _cell(row, key: str):
    """Read a column from a sqlite3.Row (or a plain dict, in tests)."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return None
