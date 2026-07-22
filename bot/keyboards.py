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


def offers_keyboard(
    lang: str, spread_id: int, purchased: frozenset[str] | set[str] = frozenset()
) -> InlineKeyboardMarkup:
    """Post-message up-sell buttons for a spread. future/+2/+5 attach to this
    spread and are once per spread, so those already in ``purchased`` are
    omitted. The "reading for a situation" button is always shown — it starts a
    fresh, independent spread and is unlimited per day."""
    p = pricing.PRICES_STARS
    rows: list[list[InlineKeyboardButton]] = []
    if pricing.FUTURE not in purchased:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_future", future=p[pricing.FUTURE]),
                    callback_data=f"buy:{pricing.FUTURE}:{spread_id}",
                )
            ]
        )
    if pricing.EXTRA_2 not in purchased:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_extra2", extra2=p[pricing.EXTRA_2]),
                    callback_data=f"buy:{pricing.EXTRA_2}:{spread_id}",
                )
            ]
        )
    if pricing.EXTRA_5 not in purchased:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_extra5", extra5=p[pricing.EXTRA_5]),
                    callback_data=f"buy:{pricing.EXTRA_5}:{spread_id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t(lang, "btn_context", context=p[pricing.CONTEXT_READING]),
                callback_data="ctx",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
