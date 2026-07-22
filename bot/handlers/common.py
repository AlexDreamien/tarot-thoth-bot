"""Basic commands: /start, /help, /lang, /cancel, /stats."""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import pricing
from ..config import Config
from ..db import Database
from ..i18n import LANGS, t
from ..keyboards import lang_keyboard
from ..service import get_lang

router = Router()


def _help_prices() -> dict[str, int]:
    p = pricing.PRICES_STARS
    return {
        "context": p[pricing.CONTEXT_READING],
        "future": p[pricing.FUTURE],
        "extra2": p[pricing.EXTRA_2],
        "extra5": p[pricing.EXTRA_5],
    }


@router.message(Command("start"))
async def cmd_start(message: Message, db: Database, cfg: Config) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(
        db, message.from_user.id, cfg.default_lang, name=message.from_user.full_name
    )
    await message.answer(t(lang, "start"))


@router.message(Command("help"))
async def cmd_help(message: Message, db: Database, cfg: Config) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    await message.answer(t(lang, "help", **_help_prices()))


@router.message(Command("lang"))
async def cmd_lang(message: Message, db: Database, cfg: Config) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    await message.answer(t(lang, "lang_prompt"), reply_markup=lang_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(callback: CallbackQuery, db: Database) -> None:
    if callback.from_user is None or callback.data is None:
        return
    lang = callback.data.split(":", 1)[1]
    if lang not in LANGS:
        await callback.answer()
        return
    await asyncio.to_thread(db.set_lang, callback.from_user.id, lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(t(lang, "lang_set"))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, db: Database, cfg: Config, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await state.clear()
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    await message.answer(t(lang, "cancelled"))


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, cfg: Config) -> None:
    if message.from_user is None or message.from_user.id not in cfg.admin_ids:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    s = await asyncio.to_thread(db.stats)
    await message.answer(t(lang, "stats", **s))
