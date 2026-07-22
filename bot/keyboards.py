"""Inline keyboards. Thin presentation layer."""

from __future__ import annotations

import calendar as _calmod

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from . import pricing
from .i18n import LANGS, _cal_labels, t


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


def calendar_keyboard(year: int, month: int, marked: set[int], lang: str) -> InlineKeyboardMarkup:
    """A month calendar (Monday-first). Days with readings (``marked``) are
    tappable (``hist:day:YYYY-MM-DD``); the rest are inert (``hist:noop``).
    Arrows navigate months (``hist:nav:YYYY-MM``)."""
    months, weekdays = _cal_labels(lang)
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="◀", callback_data=f"hist:nav:{prev_y}-{prev_m:02d}"),
            InlineKeyboardButton(text=f"{months[month - 1]} {year}", callback_data="hist:noop"),
            InlineKeyboardButton(text="▶", callback_data=f"hist:nav:{next_y}-{next_m:02d}"),
        ],
        [InlineKeyboardButton(text=wd, callback_data="hist:noop") for wd in weekdays],
    ]
    for week in _calmod.Calendar(firstweekday=0).monthdayscalendar(year, month):
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="hist:noop"))
            elif day in marked:
                row.append(
                    InlineKeyboardButton(
                        text=f"·{day}·",
                        callback_data=f"hist:day:{year}-{month:02d}-{day:02d}",
                    )
                )
            else:
                row.append(InlineKeyboardButton(text=str(day), callback_data="hist:noop"))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def day_readings_keyboard(rows_data, lang: str) -> InlineKeyboardMarkup:
    """One button per reading on a day (when there are several), plus a
    back-to-calendar button. ``rows_data`` are ``spreads`` rows for that day."""
    kb: list[list[InlineKeyboardButton]] = []
    for r in rows_data:
        if r["kind"] == "context":
            label = "✍️ " + ((r["situation"] or "").strip()[:40] or "…")
        else:
            label = t(lang, "hist_daily_label")
        kb.append([InlineKeyboardButton(text=label, callback_data=f"hist:show:{r['id']}")])
    kb.append(
        [
            InlineKeyboardButton(
                text=t(lang, "hist_back"), callback_data=f"hist:nav:{rows_data[0]['day'][:7]}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=kb)
