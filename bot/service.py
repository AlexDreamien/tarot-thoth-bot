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


def available_addons(future_bought: bool, extra_state: str) -> list[str]:
    """Add-on product codes currently offered for a spread, in display order.

    Clarifying cards are a tiered upgrade toward five total:
    - ``"none"`` → offer +2 (2⭐) or +5 (5⭐)
    - ``"two"``  → already have two, offer +3 (3⭐) to reach five (2+3 == 5⭐)
    - ``"full"`` → five already, offer nothing more
    ``future`` is an independent once-per-spread add-on.
    """
    out: list[str] = []
    if not future_bought:
        out.append(pricing.FUTURE)
    if extra_state == "none":
        out.append(pricing.EXTRA_2)
        out.append(pricing.EXTRA_5)
    elif extra_state == "two":
        out.append(pricing.EXTRA_3)
    return out


async def spread_addon_state(db: Database, spread_id: int) -> tuple[bool, str]:
    """(future_bought, extra_state) for a spread. ``extra_state`` is one of
    ``"none"`` / ``"two"`` / ``"full"`` based on how many clarifying cards were
    already bought (+2, +5, or +2 then +3)."""
    row = await asyncio.to_thread(db.get_spread, spread_id)
    counts = await asyncio.to_thread(db.extra_counts, spread_id)
    future_bought = row is not None and row["future_text"] is not None
    if 5 in counts or (2 in counts and 3 in counts):
        extra_state = "full"
    elif 2 in counts:
        extra_state = "two"
    else:
        extra_state = "none"
    return future_bought, extra_state


async def available_for_spread(db: Database, spread_id: int) -> list[str]:
    """Convenience: the up-sell product codes currently valid for a spread."""
    return available_addons(*await spread_addon_state(db, spread_id))


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
    """Paid clarifying cards (+2, +5, or +3 top-up) added to a spread and read
    within it.

    The draw excludes the spread's own cards AND any clarifying cards already
    drawn for it, so a +3 top-up never repeats the +2 cards. Deterministic per
    (spread scope, count). Returns (extra_card_ids, interpretation)."""
    row = await asyncio.to_thread(db.get_spread, spread_id)
    base_cards = split_cards(row["card_ids"])
    prior_extra = await asyncio.to_thread(db.all_extra_cards, spread_id)
    extra_key = f"{row['scope_key']}:extra:{count}"
    extra_cards = deck.draw(extra_key, count, exclude=tuple(base_cards) + tuple(prior_extra))
    extra = await asyncio.to_thread(
        db.get_or_create_extra, spread_id=spread_id, count=count, card_ids=extra_cards
    )
    if extra["interpretation"]:
        return split_cards(extra["card_ids"]), extra["interpretation"]
    text = await interp.extra(base_cards, row["interpretation"] or "", extra_cards, lang)
    await asyncio.to_thread(db.set_extra_interpretation, extra["id"], text)
    return extra_cards, text
