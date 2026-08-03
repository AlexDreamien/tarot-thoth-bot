"""Shared message-rendering helpers for the handlers."""

from __future__ import annotations

import asyncio

from aiogram.types import BufferedInputFile, Message

from .. import cards_render
from ..card_names import card_name
from ..deck import get_card
from ..i18n import t
from ..keyboards import offers_keyboard


def cards_line(lang: str, card_ids: list[str]) -> str:
    return " · ".join(card_name(get_card(c), lang) for c in card_ids)


async def send_cards_photo(message: Message, card_ids: list[str], caption: str) -> None:
    png = await asyncio.to_thread(cards_render.compose, card_ids)
    await message.answer_photo(BufferedInputFile(png, filename="spread.png"), caption=caption)


async def send_offers(
    message: Message,
    *,
    lang: str,
    spread_id: int,
    available: list[str],
    paid: bool,
    expand_cb: str | None = None,
) -> None:
    """Show the action keyboard for a spread. ``available`` comes from
    ``service.available_addons``; ``paid`` adds Stars prices to the labels;
    ``expand_cb`` offers expanding the reading just sent. Called after the daily
    spread and after every add-on message."""
    await message.answer(
        t(lang, "offers_title"),
        reply_markup=offers_keyboard(lang, spread_id, available, paid, expand_cb),
    )


async def deliver_spread(
    message: Message,
    *,
    lang: str,
    card_ids: list[str],
    interpretation: str,
    header: str,
    spread_id: int,
    available: list[str],
    paid: bool,
    expand_cb: str | None = None,
) -> None:
    """Photo (header + card names) → interpretation text → action keyboard."""
    caption = f"{header}\n{t(lang, 'cards_line', cards=cards_line(lang, card_ids))}"
    await send_cards_photo(message, card_ids, caption)
    await message.answer(interpretation)
    await send_offers(
        message,
        lang=lang,
        spread_id=spread_id,
        available=available,
        paid=paid,
        expand_cb=expand_cb,
    )
