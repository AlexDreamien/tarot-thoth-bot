"""Paid add-ons via Telegram Stars (XTR): context reading, future, extra cards.

Flow:
- future / extra cards → invoice carries the target ``spread_id`` in its payload.
- context reading → FSM: ask for the situation, then invoice; the situation
  rides in FSM state until the payment succeeds.

Stars invoices use ``currency="XTR"`` and an empty ``provider_token``.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from .. import pricing
from ..config import Config
from ..daily import day_key
from ..db import Database
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


# --- up-sell buttons -----------------------------------------------------


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    _, product, spread_id = callback.data.split(":", 2)
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    # Refuse a stale/invalid button (an add-on already bought, or a +5 after a
    # +2 that's now a +3) instead of charging Stars for a cached result.
    if product not in await available_for_spread(db, int(spread_id)):
        await callback.answer(t(lang, "already_bought"), show_alert=True)
        return
    await callback.answer()
    if isinstance(callback.message, Message):
        await _send_invoice(callback.message, lang, product, f"{product}:{spread_id}")


@router.callback_query(F.data == "ctx")
async def cb_context(callback: CallbackQuery, db: Database, cfg: Config, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    await state.set_state(ContextFlow.waiting_situation)
    if isinstance(callback.message, Message):
        await callback.message.answer(
            t(lang, "context_prompt", context=pricing.price(pricing.CONTEXT_READING))
        )


@router.message(ContextFlow.waiting_situation, F.text)
async def on_situation(message: Message, db: Database, cfg: Config, state: FSMContext) -> None:
    if message.from_user is None or message.text is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    await state.update_data(situation=message.text)
    await state.set_state(ContextFlow.waiting_payment)
    await _send_invoice(message, lang, pricing.CONTEXT_READING, f"{pricing.CONTEXT_READING}:ctx")


# --- payment lifecycle ---------------------------------------------------


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(
    message: Message,
    db: Database,
    cfg: Config,
    interp: Interpreter,
    state: FSMContext,
) -> None:
    if message.from_user is None or message.successful_payment is None:
        return
    sp = message.successful_payment
    product, ref = sp.invoice_payload.split(":", 1)
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)

    import asyncio

    await asyncio.to_thread(
        db.log_purchase,
        user_id=message.from_user.id,
        product=product,
        stars=sp.total_amount,
        charge_id=sp.telegram_payment_charge_id,
    )
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    try:
        if product == pricing.FUTURE:
            spread_id = int(ref)
            text = await ensure_future(db, interp, spread_id=spread_id, lang=lang)
            await message.answer(f"{t(lang, 'future_header')}\n\n{text}")
            await send_offers(
                message,
                lang=lang,
                spread_id=spread_id,
                available=await available_for_spread(db, spread_id),
            )

        elif product in (pricing.EXTRA_2, pricing.EXTRA_5):
            spread_id = int(ref)
            count = pricing.EXTRA_COUNT[product]
            extra_cards, text = await ensure_extra(
                db, interp, spread_id=spread_id, count=count, lang=lang
            )
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
            )

        elif product == pricing.CONTEXT_READING:
            data = await state.get_data()
            situation = data.get("situation") or ""
            await state.clear()
            row, text = await ensure_context_spread(
                db,
                interp,
                user_id=message.from_user.id,
                day=day_key(cfg.tz),
                situation=situation,
                lang=lang,
            )
            from ..db import split_cards

            await deliver_spread(
                message,
                lang=lang,
                card_ids=split_cards(row["card_ids"]),
                interpretation=text,
                header=t(lang, "context_header"),
                spread_id=row["id"],
                available=await available_for_spread(db, row["id"]),
            )
    except Exception:
        await message.answer(t(lang, "error_generic"))
        raise
