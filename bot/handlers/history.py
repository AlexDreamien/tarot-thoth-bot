"""Personal reading archive: /history → a month calendar of the user's own past
readings → tap a date → the bot replays that reading in full (date, request,
cards, interpretation, future, and any extra cards).

Every query is scoped to ``callback.from_user.id`` in SQL, so a user only ever
sees their own readings.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db import Database, split_cards
from ..i18n import t
from ..keyboards import calendar_keyboard, day_readings_keyboard
from ..service import get_lang
from .render import cards_line, send_cards_photo

router = Router()


def _marked(days: set[str], year: int, month: int) -> set[int]:
    prefix = f"{year}-{month:02d}"
    return {int(d[8:10]) for d in days if d[:7] == prefix}


async def _replay(message: Message, db: Database, lang: str, row) -> None:
    """Re-post a stored reading with all its data."""
    cards = split_cards(row["card_ids"])
    date = row["day"]
    if row["kind"] == "context":
        header = t(lang, "hist_replay_context", date=date)
    else:
        header = t(lang, "hist_replay_daily", date=date)
    caption = f"{header}\n{t(lang, 'cards_line', cards=cards_line(lang, cards))}"
    await send_cards_photo(message, cards, caption)
    if row["kind"] == "context" and (row["situation"] or "").strip():
        await message.answer(t(lang, "hist_situation", situation=row["situation"].strip()))
    if row["interpretation"]:
        await message.answer(row["interpretation"])
    if row["future_text"]:
        await message.answer(f"{t(lang, 'future_header')}\n\n{row['future_text']}")
    for extra in await asyncio.to_thread(db.extras_for_spread, row["id"]):
        ec = split_cards(extra["card_ids"])
        cap = (
            f"{t(lang, 'extra_header', n=extra['count'])}\n"
            f"{t(lang, 'cards_line', cards=cards_line(lang, ec))}"
        )
        await send_cards_photo(message, ec, cap)
        if extra["interpretation"]:
            await message.answer(extra["interpretation"])


@router.message(Command("history"))
async def cmd_history(message: Message, db: Database, cfg: Config) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(
        db, message.from_user.id, cfg.default_lang, name=message.from_user.full_name
    )
    days = await asyncio.to_thread(db.reading_day_keys, message.from_user.id)
    if not days:
        await message.answer(t(lang, "hist_empty"))
        return
    latest = max(days)  # ISO dates sort lexicographically
    year, month = int(latest[:4]), int(latest[5:7])
    await message.answer(
        t(lang, "hist_title"),
        reply_markup=calendar_keyboard(year, month, _marked(days, year, month), lang),
    )


@router.callback_query(F.data == "hist:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("hist:nav:"))
async def cb_nav(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    ym = callback.data.split(":", 2)[2]
    year, month = int(ym[:4]), int(ym[5:7])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    days = await asyncio.to_thread(db.reading_day_keys, callback.from_user.id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(
            reply_markup=calendar_keyboard(year, month, _marked(days, year, month), lang)
        )


@router.callback_query(F.data.startswith("hist:day:"))
async def cb_day(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    day = callback.data.split(":", 2)[2]
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    rows = await asyncio.to_thread(db.spreads_on_day, callback.from_user.id, day)
    await callback.answer()
    if not rows or not isinstance(callback.message, Message):
        return
    if len(rows) == 1:
        await _replay(callback.message, db, lang, rows[0])
    else:
        await callback.message.answer(
            t(lang, "hist_pick"), reply_markup=day_readings_keyboard(rows, lang)
        )


@router.callback_query(F.data.startswith("hist:show:"))
async def cb_show(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    spread_id = int(callback.data.split(":", 2)[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    row = await asyncio.to_thread(db.get_owned_spread, callback.from_user.id, spread_id)
    await callback.answer()
    if row is not None and isinstance(callback.message, Message):
        await _replay(callback.message, db, lang, row)
