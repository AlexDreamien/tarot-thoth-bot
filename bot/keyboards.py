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


# product code -> i18n button key (an icon + label, no price)
_BTN = {
    pricing.FUTURE: "btn_future",
    pricing.EXTRA_2: "btn_extra2",
    pricing.EXTRA_3: "btn_extra3",
    pricing.EXTRA_5: "btn_extra5",
}


def _label(lang: str, key: str, product: str, paid: bool) -> str:
    text = t(lang, key)
    if paid:
        text += t(lang, "price_suffix", stars=pricing.price(product))
    return text


def offers_keyboard(
    lang: str,
    spread_id: int,
    available: list[str],
    paid: bool = False,
    expand_cb: str | None = None,
) -> InlineKeyboardMarkup:
    """Post-message action buttons for a spread. ``available`` is the list of
    add-on product codes currently offered (``service.available_addons`` — hides
    bought/superseded add-ons). Labels are icon + text; when ``paid`` a
    ``— ⭐N`` price suffix is appended (Stars mode). The "reading for a
    situation" button is always appended: a context reading is a fresh,
    independent spread, unlimited per day. ``expand_cb`` (when given) adds the
    "expand this reading" button targeting the message just sent; a
    "reading for a new day" button always closes the keyboard."""
    rows: list[list[InlineKeyboardButton]] = []
    if expand_cb:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_label(lang, "btn_expand", pricing.EXPAND, paid),
                    callback_data=expand_cb,
                )
            ]
        )
    for product in available:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_label(lang, _BTN[product], product, paid),
                    callback_data=f"buy:{product}:{spread_id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=_label(lang, "btn_context", pricing.CONTEXT_READING, paid),
                callback_data="ctx",
            )
        ]
    )
    rows.append([InlineKeyboardButton(text=t(lang, "btn_newday"), callback_data="newday")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def newday_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Just the "reading for a new day" button — used by reminder messages."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_newday"), callback_data="newday")]]
    )


def _fmt_offset(minutes: int) -> str:
    sign = "+" if minutes >= 0 else "-"
    h, m = divmod(abs(minutes), 60)
    return f"{sign}{h}" + (f":{m:02d}" if m else "")


def settings_keyboard(lang: str, hour: int | None, offset_min: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t(lang, "btn_set_time"), callback_data="set:hour")],
        [
            InlineKeyboardButton(
                text=t(lang, "btn_set_tz", offset=_fmt_offset(offset_min)),
                callback_data="set:tz",
            )
        ],
    ]
    if hour is None:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_reminder_on"), callback_data="set:on")])
    else:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_reminder_off"), callback_data="set:off")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def hours_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for start in range(0, 24, 6):
        rows.append(
            [
                InlineKeyboardButton(text=f"{h:02d}:00", callback_data=f"set:hour:{h}")
                for h in range(start, start + 6)
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# UTC offsets offered in settings (whole hours, the range that covers users).
_OFFSETS = list(range(-11, 15))


def tz_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(_OFFSETS), 4):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"UTC{_fmt_offset(o * 60)}", callback_data=f"set:tz:{o * 60}"
                )
                for o in _OFFSETS[i : i + 4]
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
