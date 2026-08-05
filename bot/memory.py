"""What the reader remembers about a querent.

Pure core — no aiogram, no network, and **no clock**: rows of the querent's own
past readings go in, a compact block for the prompt comes out. "Today" is
always passed in as a day-key, so the output is deterministic and testable.

The point is continuity. Without this every reading treats the querent as a
stranger; with it the reading can say *when* a card last came up — "the Tower
again, three weeks after it stood over the same question" — which is the
difference between a card generator and a reader who knows you.

Privacy: the caller passes rows from ``db.recent_readings``, which is
user-scoped in SQL, the same rule as ``/history``. One querent's history never
reaches another's prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .card_names import card_name
from .db import split_cards
from .deck import get_card

MAX_SCANNED = 40  # past readings searched for repeats
MAX_RECENT = 6  # of those, how many are actually named in the prompt
MAX_SITUATION = 120  # a quoted question is trimmed to this many characters


@dataclass(frozen=True)
class PastReading:
    day: str  # 'YYYY-MM-DD' day-key
    kind: str  # 'daily' | 'context'
    situation: str | None  # the querent's own words, for context readings
    card_ids: tuple[str, ...]  # spread + any clarifying cards


@dataclass(frozen=True)
class Echo:
    """A card on the table today that this querent has drawn before."""

    card_id: str
    times: int  # earlier readings that held it (today's not counted)
    last_day: str
    last_situation: str | None


def _cell(row, key: str):
    """Read a column from a sqlite3.Row (or a plain dict, in tests)."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


def from_rows(rows) -> list[PastReading]:
    """Adapt ``db.recent_readings`` rows, folding clarifying cards into the
    reading they belong to — a card drawn as a clarification was on the table
    just as much as the original three."""
    out: list[PastReading] = []
    for r in rows:
        cards = split_cards(_cell(r, "card_ids") or "")
        cards += split_cards(_cell(r, "extra_card_ids") or "")
        out.append(
            PastReading(
                day=_cell(r, "day") or "",
                kind=_cell(r, "kind") or "daily",
                situation=_cell(r, "situation"),
                card_ids=tuple(cards),
            )
        )
    return out


def echoes(past: list[PastReading], current_cards: list[str]) -> list[Echo]:
    """Cards drawn today that this querent has seen before, strongest first.

    ``past`` is expected newest-first (that's the query's order), so the first
    hit for a card is its most recent one.
    """
    out: list[Echo] = []
    for cid in current_cards:
        hits = [p for p in past if cid in p.card_ids]
        if not hits:
            continue
        out.append(
            Echo(
                card_id=cid,
                times=len(hits),
                last_day=hits[0].day,
                last_situation=hits[0].situation,
            )
        )
    # Most-repeated first; ties broken by how recently it last showed up.
    out.sort(key=lambda e: (e.times, e.last_day), reverse=True)
    return out


def _trim(text: str | None) -> str:
    if not text:
        return ""
    flat = " ".join(text.split())
    return flat if len(flat) <= MAX_SITUATION else flat[: MAX_SITUATION - 1].rstrip() + "…"


def _ago(day: str, today: str) -> str:
    """'yesterday' / '13 days ago' — the model turns this into its own phrasing."""
    try:
        gap = (date.fromisoformat(today) - date.fromisoformat(day)).days
    except ValueError:
        return "earlier"
    if gap <= 0:
        return "earlier today"
    if gap == 1:
        return "yesterday"
    return f"{gap} days ago"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:  # 11th, 12th, 13th — not 11st
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _names(card_ids: tuple[str, ...] | list[str], lang: str) -> str:
    return " · ".join(card_name(get_card(c), lang) for c in card_ids)


def render_block(
    past: list[PastReading], current_cards: list[str], lang: str, *, today: str
) -> str:
    """The memory section of the prompt. Empty string when there's no history —
    a first-time querent must not get a reading that gestures at a past."""
    if not past:
        return ""
    lines = [
        "This querent's own earlier readings, most recent first "
        "(their private history — it is real, use it as fact):"
    ]
    for p in past[:MAX_RECENT]:
        kind = "reading for a situation" if p.kind == "context" else "daily reading"
        head = f"- {p.day} ({_ago(p.day, today)}, {kind}"
        if p.situation:
            head += f", they asked about «{_trim(p.situation)}»"
        lines.append(f"{head}): {_names(p.card_ids, lang)}")

    recurring = echoes(past, current_cards)
    if recurring:
        lines += ["", "Cards on the table today that this querent has drawn before:"]
        for e in recurring:
            tail = f", while asking about «{_trim(e.last_situation)}»" if e.last_situation else ""
            lines.append(
                f"- {card_name(get_card(e.card_id), lang)} — {_ordinal(e.times + 1)} time; "
                f"last seen {e.last_day} ({_ago(e.last_day, today)}{tail})."
            )
    return "\n".join(lines)
