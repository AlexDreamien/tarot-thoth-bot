"""/settings — the daily-reminder preferences: hour, UTC offset, on/off.

Telegram does not expose a user's time zone, so the user picks their UTC offset
here; the scheduler uses it to fire at their local hour. With reminders off the
scheduler still sends one silent weekly nudge.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from .. import style as style_mod
from ..config import Config
from ..db import Database
from ..i18n import t
from ..keyboards import (
    _fmt_offset,
    hours_keyboard,
    settings_keyboard,
    style_keyboard,
    style_name,
    tz_keyboard,
)
from ..service import get_lang, user_style

router = Router()


def _state_text(lang: str, hour: int | None, offset_min: int) -> str:
    if hour is None:
        return t(lang, "settings_state_off")
    return t(lang, "settings_state_on", hour=f"{hour:02d}", offset=_fmt_offset(offset_min))


async def _show(
    message: Message, db: Database, lang: str, user_id: int, edit: bool = False
) -> None:
    user = await asyncio.to_thread(db.get_user, user_id)
    hour = user["reminder_hour"] if user else None
    offset = (user["tz_offset_min"] if user else None) or 0
    text = t(lang, "settings_title", state=_state_text(lang, hour, offset))
    kb = settings_keyboard(lang, hour, offset, await user_style(db, user_id))
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.message(Command("settings"))
async def cmd_settings(message: Message, db: Database, cfg: Config) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    await _show(message, db, lang, message.from_user.id)


@router.callback_query(F.data == "set:hour")
async def cb_pick_hour(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "pick_hour"), reply_markup=hours_keyboard())


@router.callback_query(F.data == "set:tz")
async def cb_pick_tz(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "pick_tz"), reply_markup=tz_keyboard())


@router.callback_query(F.data == "set:style")
async def cb_pick_style(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    current = await user_style(db, callback.from_user.id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            t(lang, "pick_style"), reply_markup=style_keyboard(lang, current)
        )


@router.callback_query(F.data.startswith("set:style:"))
async def cb_set_style(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    """Applies to readings generated from now on; already-cached ones keep the
    voice they were written in."""
    if callback.from_user is None or callback.data is None:
        return
    chosen = style_mod.normalize(callback.data.split(":")[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_style, callback.from_user.id, chosen)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "style_saved", style=style_name(lang, chosen)))


@router.callback_query(F.data.startswith("set:hour:"))
async def cb_set_hour(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    hour = int(callback.data.split(":")[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_reminder_hour, callback.from_user.id, hour)
    await callback.answer()
    await _finish(callback, db, lang)


@router.callback_query(F.data.startswith("set:tz:"))
async def cb_set_tz(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    minutes = int(callback.data.split(":")[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_tz_offset, callback.from_user.id, minutes)
    await callback.answer()
    await _finish(callback, db, lang)


@router.callback_query(F.data.in_({"set:off", "set:on"}))
async def cb_toggle(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    from ..db import DEFAULT_REMINDER_HOUR

    hour = None if callback.data == "set:off" else DEFAULT_REMINDER_HOUR
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_reminder_hour, callback.from_user.id, hour)
    await callback.answer()
    await _finish(callback, db, lang)


async def _finish(callback: CallbackQuery, db: Database, lang: str) -> None:
    user = await asyncio.to_thread(db.get_user, callback.from_user.id)
    state = _state_text(lang, user["reminder_hour"], user["tz_offset_min"] or 0)
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "settings_saved", state=state))
