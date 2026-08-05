"""Shared message-rendering helpers for the handlers."""

from __future__ import annotations

import asyncio
import html
from contextlib import asynccontextmanager, suppress

from aiogram.types import BufferedInputFile, Message

from .. import cards_render
from ..card_names import card_name
from ..deck import get_card
from ..i18n import t
from ..keyboards import offers_keyboard

# Telegram rejects messages over 4096 characters ("message is too long"), and
# expanded readings routinely exceed that — always send generated text through
# answer_long().
TG_LIMIT = 3900

# Telegram drops the "typing…" indicator about five seconds after it is set, so
# it has to be re-sent for as long as the model is working — a reading takes
# anywhere from twenty seconds to two minutes. Refresh slightly early so the
# indicator never visibly blinks out between actions.
TYPING_REFRESH = 4.0


def split_text(text: str, limit: int = TG_LIMIT) -> list[str]:
    """Split text into Telegram-sized chunks, preferring paragraph, then line,
    then sentence boundaries; hard-splits only as a last resort."""
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []

    chunks: list[str] = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if chunks and len(chunks[-1]) + 2 + len(para) <= limit:
            chunks[-1] = f"{chunks[-1]}\n\n{para}"
        elif len(para) <= limit:
            chunks.append(para)
        else:
            chunks.extend(_split_long(para, limit))
    return chunks


def _split_long(para: str, limit: int) -> list[str]:
    """A single paragraph that is itself over the limit."""
    out: list[str] = []
    rest = para
    while len(rest) > limit:
        window = rest[:limit]
        cut = max(window.rfind("\n"), window.rfind(". "), window.rfind("! "), window.rfind("? "))
        cut = cut + 1 if cut > limit // 2 else limit  # keep the delimiter
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        out.append(rest)
    return out


async def answer_long(message: Message, text: str, header: str | None = None) -> None:
    """Send model-generated text safely: HTML-escaped (the bot's parse_mode is
    HTML, and a stray '<' or '&' in a reading would be rejected), prefixed with
    an optional already-formatted ``header``, and split across messages if it
    exceeds Telegram's length limit."""
    body = html.escape(text, quote=False)
    if header:
        body = f"{header}\n\n{body}"
    for chunk in split_text(body):
        await message.answer(chunk)


async def send_action(message: Message, action: str) -> None:
    """Set a chat action ("typing…", "sending photo…").

    Best-effort by design: the indicator is decoration, and a failed action —
    or a message object that carries no bot, as in the unit tests — must never
    take a reading down with it.
    """
    with suppress(Exception):
        await message.bot.send_chat_action(chat_id=message.chat.id, action=action)


async def _keep_typing(message: Message) -> None:
    """Hold the "typing…" indicator up until cancelled."""
    while True:
        await send_action(message, "typing")
        await asyncio.sleep(TYPING_REFRESH)


@asynccontextmanager
async def thinking(message: Message, lang: str):
    """Show a "composing your reading…" placeholder and a live "typing…"
    indicator while the model works, then clear both just before the result.

    Generation can take a minute or two. A chat action expires after ~5s, so it
    is re-sent on a loop for the whole wait; the placeholder message says what
    is being waited for. Wrap ONLY the generation call — both are torn down on
    exit, so send the result after the block.
    """
    note = None
    with suppress(Exception):
        note = await message.answer(t(lang, "generating"))
    typing = asyncio.create_task(_keep_typing(message))
    try:
        yield
    finally:
        typing.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await typing
        if note is not None:
            with suppress(Exception):  # already deleted / too old / no rights
                await note.delete()


def cards_line(lang: str, card_ids: list[str]) -> str:
    return " · ".join(card_name(get_card(c), lang) for c in card_ids)


async def send_cards_photo(message: Message, card_ids: list[str], caption: str) -> None:
    # Compositing and uploading takes a beat, right after the "typing…" loop has
    # stopped — without this the chat goes quiet again at the last moment.
    await send_action(message, "upload_photo")
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
    await answer_long(message, interpretation)
    await send_offers(
        message,
        lang=lang,
        spread_id=spread_id,
        available=available,
        paid=paid,
        expand_cb=expand_cb,
    )
