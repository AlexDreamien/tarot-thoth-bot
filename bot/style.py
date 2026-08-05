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

# Both are interpolated into the system prompt, so both are length-capped and
# flattened to a single line: neither is a place to smuggle instructions from.
MAX_NAME = 32
MAX_BIO = 600  # a solid paragraph — enough context without swamping the reading


def normalize_gender(value: str | None) -> str | None:
    """A stored gender, or None — which means *unknown*, not "default to male".
    Readings then avoid gendered agreement altogether."""
    return value if value in GENDERS else None


def _flatten(raw: str | None, limit: int) -> str | None:
    """Sanitise free text for interpolation into a prompt: one line, trimmed,
    length-capped, no guillemets (they delimit it there). None if nothing
    usable is left."""
    if not raw:
        return None
    flat = " ".join(raw.split())  # collapses newlines and runs of whitespace
    flat = flat.replace("«", "").replace("»", "").strip()
    return flat[:limit] or None


def clean_name(raw: str | None) -> str | None:
    """A self-chosen name, fit to put in a prompt."""
    return _flatten(raw, MAX_NAME)


def clean_bio(raw: str | None) -> str | None:
    """What the querent told the bot about themselves, fit to put in a prompt."""
    return _flatten(raw, MAX_BIO)


@dataclass(frozen=True)
class Persona:
    """Everything the model is told about *who it is talking to and how*."""

    style: str = DEFAULT
    gender: str | None = None  # None == unknown, write genderless
    name: str | None = None  # None == no name, address them directly
    bio: str | None = None  # optional self-description, used as background

    @classmethod
    def from_row(cls, row) -> Persona:
        """Build from a ``users`` row (or None, for a user we've never stored)."""
        if row is None:
            return cls()
        return cls(
            style=normalize(_cell(row, "style")),
            gender=normalize_gender(_cell(row, "gender")),
            name=clean_name(_cell(row, "display_name")),
            bio=clean_bio(_cell(row, "bio")),
        )


def _cell(row, key: str):
    """Read a column from a sqlite3.Row (or a plain dict, in tests)."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return None
