"""Inline keyboards. Thin presentation layer."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from . import pricing
from .i18n import LANGS, t


def lang_keyboard() -> InlineKeyboardMarkup:
    from .i18n import _STRINGS  # localized language names

    rows = [
        [InlineKeyboardButton(text=_STRINGS[lang]["lang_name"], callback_data=f"lang:{lang}")]
        for lang in LANGS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# product code -> (i18n button key, the format kwarg that carries the price)
_BTN = {
    pricing.FUTURE: ("btn_future", "future"),
    pricing.EXTRA_2: ("btn_extra2", "extra2"),
    pricing.EXTRA_3: ("btn_extra3", "extra3"),
    pricing.EXTRA_5: ("btn_extra5", "extra5"),
}


def offers_keyboard(lang: str, spread_id: int, available: list[str]) -> InlineKeyboardMarkup:
    """Post-message up-sell buttons for a spread. ``available`` is the list of
    add-on product codes currently offered (computed by
    ``service.available_addons`` — hides bought/superseded add-ons). The
    "reading for a situation" button is always appended: a context reading is a
    fresh, independent spread and is unlimited per day."""
    rows: list[list[InlineKeyboardButton]] = []
    for product in available:
        key, kw = _BTN[product]
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, key, **{kw: pricing.price(product)}),
                    callback_data=f"buy:{product}:{spread_id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "btn_context", context=pricing.price(pricing.CONTEXT_READING)),
                callback_data="ctx",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
