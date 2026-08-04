"""The free daily three-card spread: /tarot, and the shared delivery helper the
"reading for a new day" button reuses."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import Config
from ..daily import day_key
from ..db import Database, split_cards
from ..i18n import t
from ..interpret import Interpreter
from ..service import available_for_spread, ensure_daily_spread, get_lang
from .render import deliver_spread, thinking

router = Router()


async def deliver_daily(
    message: Message,
    db: Database,
    cfg: Config,
    interp: Interpreter,
    lang: str,
    user_id: int,
) -> None:
    """Draw (or re-send) today's spread and deliver it with the action buttons."""
    day = day_key(cfg.tz)
    try:
        async with thinking(message, lang):
            row, interpretation = await ensure_daily_spread(
                db, interp, user_id=user_id, day=day, lang=lang
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
        paid=cfg.payments_enabled,
        expand_cb=f"exp:s:{row['id']}",
    )


@router.message(Command("tarot"))
async def cmd_tarot(message: Message, db: Database, cfg: Config, interp: Interpreter) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(
        db, message.from_user.id, cfg.default_lang, name=message.from_user.full_name
    )
    await deliver_daily(message, db, cfg, interp, lang, message.from_user.id)
