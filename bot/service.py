"""High-level operations shared by the handlers.

Ties together the pure core (deck, db, interpret prompts) with the IO boundary
(SQLite in a thread, the async Claude call). Each op is idempotent: the drawn
cards and the generated interpretation are persisted, so a repeated request —
or a retried payment — returns the stored result instead of re-drawing or
re-billing the model.
"""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3

from . import deck, pricing
from .db import Database, split_cards
from .interpret import Interpreter


def _situation_hash(situation: str) -> str:
    return hashlib.sha256(situation.strip().encode("utf-8")).hexdigest()[:8]


async def purchased_addons(db: Database, spread_id: int) -> set[str]:
    """Product codes of the add-ons already consumed for this spread. Each
    add-on (future, +2, +5) is once per spread; the up-sell keyboard hides the
    ones already here, and the buy handler refuses to re-charge them."""
    row = await asyncio.to_thread(db.get_spread, spread_id)
    counts = await asyncio.to_thread(db.extra_counts, spread_id)
    out: set[str] = set()
    if row is not None and row["future_text"] is not None:
        out.add(pricing.FUTURE)
    if pricing.EXTRA_COUNT[pricing.EXTRA_2] in counts:
        out.add(pricing.EXTRA_2)
    if pricing.EXTRA_COUNT[pricing.EXTRA_5] in counts:
        out.add(pricing.EXTRA_5)
    return out


async def get_lang(db: Database, user_id: int, default_lang: str) -> str:
    return await asyncio.to_thread(db.get_or_create_user, user_id, default_lang)


async def ensure_daily_spread(
    db: Database, interp: Interpreter, *, user_id: int, day: str, lang: str
) -> tuple[sqlite3.Row, str]:
    """The free daily spread — fixed per (user, day). Draws once, interprets
    once, caches both."""
    scope_key = f"{user_id}:{day}:daily"
    cards = deck.draw(scope_key, 3)
    row = await asyncio.to_thread(
        db.get_or_create_spread,
        user_id=user_id,
        day=day,
        kind="daily",
        scope_key=scope_key,
        card_ids=cards,
    )
    return await _ensure_interpretation(db, interp, row, lang, kind="daily")


async def ensure_context_spread(
    db: Database, interp: Interpreter, *, user_id: int, day: str, situation: str, lang: str
) -> tuple[sqlite3.Row, str]:
    """A paid spread laid for a specific described situation."""
    scope_key = f"{user_id}:{day}:context:{_situation_hash(situation)}"
    cards = deck.draw(scope_key, 3)
    row = await asyncio.to_thread(
        db.get_or_create_spread,
        user_id=user_id,
        day=day,
        kind="context",
        scope_key=scope_key,
        card_ids=cards,
        situation=situation,
    )
    return await _ensure_interpretation(db, interp, row, lang, kind="context")


async def _ensure_interpretation(
    db: Database, interp: Interpreter, row: sqlite3.Row, lang: str, *, kind: str
) -> tuple[sqlite3.Row, str]:
    if row["interpretation"]:
        return row, row["interpretation"]
    cards = split_cards(row["card_ids"])
    if kind == "context":
        text = await interp.context(cards, row["situation"], lang)
    else:
        text = await interp.daily(cards, lang)
    await asyncio.to_thread(db.set_interpretation, row["id"], text)
    return await asyncio.to_thread(db.get_spread, row["id"]), text


async def ensure_future(db: Database, interp: Interpreter, *, spread_id: int, lang: str) -> str:
    """Paid future-looking reading appended to an existing spread. Cached."""
    row = await asyncio.to_thread(db.get_spread, spread_id)
    if row["future_text"]:
        return row["future_text"]
    text = await interp.future(split_cards(row["card_ids"]), row["interpretation"] or "", lang)
    await asyncio.to_thread(db.set_future, spread_id, text)
    return text


async def ensure_extra(
    db: Database, interp: Interpreter, *, spread_id: int, count: int, lang: str
) -> tuple[list[str], str]:
    """Paid clarifying cards (2 or 5) added to a spread and read within it.

    Extra cards exclude the spread's own cards; the draw is deterministic per
    (spread scope, count). Returns (extra_card_ids, interpretation)."""
    row = await asyncio.to_thread(db.get_spread, spread_id)
    base_cards = split_cards(row["card_ids"])
    extra_key = f"{row['scope_key']}:extra:{count}"
    extra_cards = deck.draw(extra_key, count, exclude=tuple(base_cards))
    extra = await asyncio.to_thread(
        db.get_or_create_extra, spread_id=spread_id, count=count, card_ids=extra_cards
    )
    if extra["interpretation"]:
        return split_cards(extra["card_ids"]), extra["interpretation"]
    text = await interp.extra(base_cards, row["interpretation"] or "", extra_cards, lang)
    await asyncio.to_thread(db.set_extra_interpretation, extra["id"], text)
    return extra_cards, text
