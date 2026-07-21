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


def offers_keyboard(lang: str, spread_id: int) -> InlineKeyboardMarkup:
    """Post-spread up-sell buttons. Future/extras attach to this spread;
    context starts a new flow."""
    p = pricing.PRICES_STARS
    rows = [
        [
            InlineKeyboardButton(
                text=t(lang, "btn_future", future=p[pricing.FUTURE]),
                callback_data=f"buy:{pricing.FUTURE}:{spread_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "btn_extra2", extra2=p[pricing.EXTRA_2]),
                callback_data=f"buy:{pricing.EXTRA_2}:{spread_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "btn_extra5", extra5=p[pricing.EXTRA_5]),
                callback_data=f"buy:{pricing.EXTRA_5}:{spread_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "btn_context", context=p[pricing.CONTEXT_READING]),
                callback_data="ctx",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
