"""The free daily three-card spread: /tarot (and /start's natural next step)."""

from __future__ import annotations

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message

from ..config import Config
from ..daily import day_key
from ..db import Database, split_cards
from ..i18n import t
from ..interpret import Interpreter
from ..service import available_for_spread, ensure_daily_spread, get_lang
from .render import deliver_spread

router = Router()


@router.message(Command("tarot"))
async def cmd_tarot(message: Message, db: Database, cfg: Config, interp: Interpreter) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    day = day_key(cfg.tz)
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        row, interpretation = await ensure_daily_spread(
            db, interp, user_id=message.from_user.id, day=day, lang=lang
        )
    except Exception:
        await message.answer(t(lang, "error_generic"))
        raise
    await deliver_spread(
        message,
        lang=lang,
        card_ids=split_cards(row["card_ids"]),
        interpretation=interpretation,
        header=t(lang, "daily_header", date=day),
        spread_id=row["id"],
        available=await available_for_spread(db, row["id"]),
    )
