"""/settings — every preference: reminder hour, UTC offset, on/off, the voice of
the readings, how the querent is addressed, and the language.

Telegram does not expose a user's time zone, so the user picks their UTC offset
here; the scheduler uses it to fire at their local hour. With reminders off the
scheduler still sends one silent weekly nudge.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import style as style_mod
from ..config import Config
from ..db import Database
from ..i18n import t
from ..keyboards import (
    _fmt_offset,
    address_keyboard,
    bio_keyboard,
    gender_name,
    hours_keyboard,
    lang_keyboard,
    settings_keyboard,
    style_keyboard,
    style_name,
    tz_keyboard,
)
from ..service import get_lang, user_persona

router = Router()


class NameFlow(StatesGroup):
    waiting_name = State()


class BioFlow(StatesGroup):
    waiting_bio = State()


def _state_text(lang: str, hour: int | None, offset_min: int) -> str:
    if hour is None:
        return t(lang, "settings_state_off")
    return t(lang, "settings_state_on", hour=f"{hour:02d}", offset=_fmt_offset(offset_min))


async def _show(
    message: Message, db: Database, lang: str, user_id: int, edit: bool = False
) -> None:
    user = await asyncio.to_thread(db.get_user, user_id)
    hour = user["reminder_hour"] if user else None
    offset = (user["tz_offset_min"] if user else None) or 0
    text = t(lang, "settings_title", state=_state_text(lang, hour, offset))
    kb = settings_keyboard(lang, hour, offset, style_mod.Persona.from_row(user))
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.message(Command("settings"))
async def cmd_settings(message: Message, db: Database, cfg: Config) -> None:
    if message.from_user is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    await _show(message, db, lang, message.from_user.id)


@router.callback_query(F.data == "set:hour")
async def cb_pick_hour(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "pick_hour"), reply_markup=hours_keyboard())


@router.callback_query(F.data == "set:tz")
async def cb_pick_tz(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "pick_tz"), reply_markup=tz_keyboard())


async def _show_address(message: Message, db: Database, lang: str, user_id: int) -> None:
    who = await user_persona(db, user_id)
    await message.answer(
        t(
            lang,
            "address_title",
            gender=gender_name(lang, who.gender),
            name=who.name or t(lang, "address_unset"),
        ),
        reply_markup=address_keyboard(lang, who),
    )


@router.callback_query(F.data == "set:address")
async def cb_address(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_address(callback.message, db, lang, callback.from_user.id)


@router.callback_query(F.data.startswith("set:gender:"))
async def cb_set_gender(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    """ "none" clears it — which means genderless readings, not masculine ones."""
    if callback.from_user is None or callback.data is None:
        return
    gender = style_mod.normalize_gender(callback.data.split(":")[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_gender, callback.from_user.id, gender)
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_address(callback.message, db, lang, callback.from_user.id)


@router.callback_query(F.data == "set:name:clear")
async def cb_clear_name(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_display_name, callback.from_user.id, None)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "name_cleared"))


@router.callback_query(F.data == "set:name")
async def cb_ask_name(
    callback: CallbackQuery, db: Database, cfg: Config, state: FSMContext
) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    await state.set_state(NameFlow.waiting_name)
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "name_prompt"))


@router.message(NameFlow.waiting_name, F.text)
async def on_name(message: Message, db: Database, cfg: Config, state: FSMContext) -> None:
    """The name is interpolated into the system prompt, so it is sanitised to one
    short line first — see ``style.clean_name``."""
    if message.from_user is None or message.text is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    name = style_mod.clean_name(message.text)
    if not name:
        await message.answer(t(lang, "name_too_odd"))
        return
    await state.clear()
    await asyncio.to_thread(db.set_display_name, message.from_user.id, name)
    await message.answer(t(lang, "name_saved", name=name))


async def _show_bio(message: Message, db: Database, lang: str, user_id: int) -> None:
    who = await user_persona(db, user_id)
    await message.answer(
        t(lang, "bio_title", bio=who.bio or t(lang, "bio_empty")),
        reply_markup=bio_keyboard(lang, who),
    )


@router.callback_query(F.data == "set:bio:show")
async def cb_bio(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_bio(callback.message, db, lang, callback.from_user.id)


@router.callback_query(F.data == "set:bio:clear")
async def cb_clear_bio(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_bio, callback.from_user.id, None)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "bio_cleared"))


@router.callback_query(F.data == "set:bio")
async def cb_ask_bio(callback: CallbackQuery, db: Database, cfg: Config, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    await state.set_state(BioFlow.waiting_bio)
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "bio_prompt"))


@router.message(BioFlow.waiting_bio, F.text)
async def on_bio(message: Message, db: Database, cfg: Config, state: FSMContext) -> None:
    """Too long is refused rather than silently truncated — the querent should
    know what the bot actually kept."""
    if message.from_user is None or message.text is None:
        return
    lang = await get_lang(db, message.from_user.id, cfg.default_lang)
    if len(message.text.strip()) > style_mod.MAX_BIO:
        await message.answer(
            t(lang, "bio_too_long", limit=style_mod.MAX_BIO, got=len(message.text.strip()))
        )
        return
    bio = style_mod.clean_bio(message.text)
    await state.clear()
    await asyncio.to_thread(db.set_bio, message.from_user.id, bio)
    await message.answer(t(lang, "bio_saved" if bio else "bio_cleared"))


@router.callback_query(F.data == "settings:open")
async def cb_open_settings(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    """The button on the first-run welcome message."""
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show(callback.message, db, lang, callback.from_user.id)


@router.callback_query(F.data == "set:lang")
async def cb_pick_lang(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    """The language picker now lives in /settings; the `lang:<code>` callbacks
    it produces are still handled in ``handlers.common``."""
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "lang_prompt"), reply_markup=lang_keyboard())


@router.callback_query(F.data == "set:style")
async def cb_pick_style(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None:
        return
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    current = (await user_persona(db, callback.from_user.id)).style
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            t(lang, "pick_style"), reply_markup=style_keyboard(lang, current)
        )


@router.callback_query(F.data.startswith("set:style:"))
async def cb_set_style(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    """Applies to readings generated from now on; already-cached ones keep the
    voice they were written in."""
    if callback.from_user is None or callback.data is None:
        return
    chosen = style_mod.normalize(callback.data.split(":")[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_style, callback.from_user.id, chosen)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "style_saved", style=style_name(lang, chosen)))


@router.callback_query(F.data.startswith("set:hour:"))
async def cb_set_hour(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    hour = int(callback.data.split(":")[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_reminder_hour, callback.from_user.id, hour)
    await callback.answer()
    await _finish(callback, db, lang)


@router.callback_query(F.data.startswith("set:tz:"))
async def cb_set_tz(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    minutes = int(callback.data.split(":")[2])
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_tz_offset, callback.from_user.id, minutes)
    await callback.answer()
    await _finish(callback, db, lang)


@router.callback_query(F.data.in_({"set:off", "set:on"}))
async def cb_toggle(callback: CallbackQuery, db: Database, cfg: Config) -> None:
    if callback.from_user is None or callback.data is None:
        return
    from ..db import DEFAULT_REMINDER_HOUR

    hour = None if callback.data == "set:off" else DEFAULT_REMINDER_HOUR
    lang = await get_lang(db, callback.from_user.id, cfg.default_lang)
    await asyncio.to_thread(db.set_reminder_hour, callback.from_user.id, hour)
    await callback.answer()
    await _finish(callback, db, lang)


async def _finish(callback: CallbackQuery, db: Database, lang: str) -> None:
    user = await asyncio.to_thread(db.get_user, callback.from_user.id)
    state = _state_text(lang, user["reminder_hour"], user["tz_offset_min"] or 0)
    if isinstance(callback.message, Message):
        await callback.message.answer(t(lang, "settings_saved", state=state))
