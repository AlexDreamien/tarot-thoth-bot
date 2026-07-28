"""Spread add-ons: a look at the future, extra clarifying cards, and a reading
for a described situation.

Gated by ``cfg.payments_enabled``:
- **off** (default) — tapping a button delivers the add-on for free, right away.
- **on** — the add-on is sold for Telegram Stars (XTR): future/extra buttons
  send an invoice carrying the target ``spread_id`` in the payload; the context
  flow asks for the situation, then invoices (the situation rides in FSM state
  until the payment succeeds). Stars invoices use ``currency="XTR"`` and an
  empty ``provider_token``.

Either way the once-per-spread rules (``service.available_addons``) apply.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from .. import pricing
from ..config import Config
from ..daily import day_key
from ..db import Database, split_cards
from ..i18n import t
from ..interpret import Interpreter
from ..service import (
    available_for_spread,
    ensure_context_spread,
    ensure_extra,
    ensure_future,
    get_lang,
)
from .render import cards_line, deliver_spread, send_cards_photo, send_offers

router = Router()

# product code -> i18n key suffix for the invoice title/description
_I18N_SUFFIX = {
    pricing.CONTEXT_READING: "context",
    pricing.FUTURE: "future",
    pricing.EXTRA_2: "extra2",
    pricing.EXTRA_5: "extra5",
    pricing.EXTRA_3: "extra3",
}


class ContextFlow(StatesGroup):
    waiting_situation = State()
    waiting_payment = State()


# --- delivery (shared by the free and the paid paths) --------------------


async def _deliver_future(message, db, interp, cfg, lang, spread_id):
    text = await ensure_future(db, interp, spread_id=spread_id, lang=lang)
    await message.answer(f"{t(lang, 'future_header')}\n\n{text}")
    await send_offers(
        message,
        lang=lang,
        spread_id=spread_id,
        available=await available_for_spread(db, spread_id),
        paid=cfg.payments_enabled,
    )


async def _deliver_extra(message, db, interp, cfg, lang, spread_id, count):
    extra_cards, text = await ensure_extra(db, interp, spread_id=spread_id, count=count, lang=lang)
    caption = (
        f"{t(lang, 'extra_header', n=count)}\n"
        f"{t(lang, 'cards_line', cards=cards_line(lang, extra_cards))}"
    )
    await send_cards_photo(message, extra_cards, caption)
    await message.answer(text)
    await send_offers(
        message,
        lang=lang,
        spread_id=spread_id,
        available=await available_for_spread(db, spread_id),
        paid=cfg.payments_enabled,
    )


async def _deliver_addon(message, db, interp, cfg, lang, product, spread_id):
    if product == pricing.FUTURE:
        await _deliver_future(message, db, interp, cfg, lang, spread_id)
    else:  # extra_2 / extra_3 / extra_5
        await _deliver_extra(
            message, db, interp, cfg, lang, spread_id, pricing.EXTRA_COUNT[product]
        )


async def _deliver_context(message, db, interp, cfg, lang, user_id, situation):
    row, text = await ensure_context_spread(
        db, interp, user_id=user_id, day=day_key(cfg.tz), situation=situation, lang=lang
    )
    await deliver_spread(
        message,
        lang=lang,
        card_ids=split_cards(row["card_ids"]),
        interpretation=text,
        header=t(lang, "context_header"),
        spread_id=row["id"],
        available=await available_for_spread(db, row["id"]),
        paid=cfg.payments_enabled,
    )


async def _send_invoice(message: Message, lang: str, product: str, payload: str) -> None:
    suffix = _I18N_SUFFIX[product]
    stars = pricing.price(product)
    await message.answer_invoice(
        title=t(lang, f"invoice_title_{suffix}"),
        description=t(lang, f"invoice_desc_{suffix}"),
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=t(lang, f"invoice_title_{suffix}"), amount=stars)],
        provider_token="",
    )


# --- action buttons ------------------------------------------------------


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery, db: Database, cfg: Config, interp: Interpreter) -> None:
    if callback.from_user is None or callback.data is None:
        return
    _, product, spread_id = callback.data.split(":", 2)
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    # Refuse a stale/invalid button (an add-on already bought, or a +5 after a
    # +2 that's now a +3).
    if product not in await available_for_spread(db, int(spread_id)):
        await callback.answer(t(lang, "already_bought"), show_alert=True)
        return
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    if cfg.payments_enabled:
        await _send_invoice(callback.message, lang, product, f"{product}:{spread_id}")
        return
    await callback.message.bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    try:
        await _deliver_addon(callback.message, db, interp, cfg, lang, product, int(spread_id))
    except Exception:
        await callback.message.answer(t(lang, "error_generic"))
        raise


@router.callback_query(F.data == "ctx")
async def cb_context(callback: CallbackQuery, db: Database, cfg: Config, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    await state.set_state(ContextFlow.waiting_situation)
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "context_prompt"))


@router.message(ContextFlow.waiting_situation, F.text)
async def on_situation(
    message: Message, db: Database, cfg: Config, interp: Interpreter, state: FSMContext
) -> None:
    if message.from_user is None or message.text is None:
        return
    lang = await get_lang(
        db, message.from_user.id, cfg.default_lang, name=message.from_user.full_name
    )
    situation = message.text
    if cfg.payments_enabled:
        await state.update_data(situation=situation)
        await state.set_state(ContextFlow.waiting_payment)
        await _send_invoice(
            message, lang, pricing.CONTEXT_READING, f"{pricing.CONTEXT_READING}:ctx"
        )
        return
    await state.clear()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        await _deliver_context(message, db, interp, cfg, lang, message.from_user.id, situation)
    except Exception:
        await message.answer(t(lang, "error_generic"))
        raise


# --- Stars payment lifecycle (only reached when payments_enabled) ---------


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(
    message: Message, db: Database, cfg: Config, interp: Interpreter, state: FSMContext
) -> None:
    if message.from_user is None or message.successful_payment is None:
        return
    sp = message.successful_payment
    product, ref = sp.invoice_payload.split(":", 1)
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    await asyncio.to_thread(
        db.log_purchase,
        user_id=message.from_user.id,
        product=product,
        stars=sp.total_amount,
        charge_id=sp.telegram_payment_charge_id,
    )
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        if product == pricing.CONTEXT_READING:
            situation = (await state.get_data()).get("situation") or ""
            await state.clear()
            await _deliver_context(message, db, interp, cfg, lang, message.from_user.id, situation)
        else:
            await _deliver_addon(message, db, interp, cfg, lang, product, int(ref))
    except Exception:
        await message.answer(t(lang, "error_generic"))
        raise
