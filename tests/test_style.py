import asyncio

import pytest

from bot import interpret, style
from bot.db import Database
from bot.i18n import LANGS, t
from bot.keyboards import settings_keyboard, style_keyboard
from bot.service import user_style


def _datas(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def test_the_default_voice_leaves_the_prompt_exactly_as_it_was():
    # Nothing is appended for the original persona, so every user who never
    # touches the setting keeps the prompt the bot has always sent.
    assert interpret.system_prompt("ru") == interpret.system_prompt("ru", style=style.FORTUNE)
    assert interpret.system_prompt("ru", style=None) == interpret.system_prompt("ru")


@pytest.mark.parametrize("code", [style.PSY, style.LOGIC, style.BUDDY])
def test_each_other_voice_changes_the_prompt(code):
    plain = interpret.system_prompt("ru")
    voiced = interpret.system_prompt("ru", style=code)
    assert voiced != plain
    assert voiced.startswith(plain)  # the voice is appended, nothing is lost
    assert "VOICE" in voiced


def test_the_voice_never_overrides_the_product_rule():
    # Whatever the persona, a reading still describes the present and refuses to
    # predict — that is the premise, not a stylistic choice.
    for code in style.STYLES:
        sys = interpret.system_prompt("ru", style=code).lower()
        assert "current disposition" in sys
        assert "do not predict" in sys


def test_the_voice_reaches_the_future_and_deep_prompts_too():
    assert "VOICE" in interpret.future_system_prompt("ru", style=style.BUDDY)
    assert "VOICE" in interpret.system_prompt("ru", deep=True, style=style.LOGIC)


def test_an_unknown_or_missing_code_falls_back_to_the_default():
    # A style dropped from STYLES in a later version must not break stored rows.
    assert style.normalize(None) == style.DEFAULT
    assert style.normalize("tarot_pirate") == style.DEFAULT
    assert interpret.system_prompt("ru", style="tarot_pirate") == interpret.system_prompt("ru")


def test_every_style_has_a_label_in_every_language():
    for code in style.STYLES:
        for lang in LANGS:
            label = t(lang, f"style_{code}")
            assert label != f"style_{code}", f"{lang}/{code} has no label"
            assert label.strip()


def test_style_keyboard_ticks_the_active_voice():
    kb = style_keyboard("ru", style.LOGIC)
    assert _datas(kb) == [f"set:style:{c}" for c in style.STYLES]
    ticked = [b.text for row in kb.inline_keyboard for b in row if b.text.startswith("✅")]
    assert len(ticked) == 1
    assert t("ru", "style_logic") in ticked[0]


def test_settings_offers_the_style_button():
    kb = settings_keyboard("ru", 9, 180, style.BUDDY)
    assert "set:style" in _datas(kb)
    label = [b.text for row in kb.inline_keyboard for b in row if b.callback_data == "set:style"][0]
    assert t("ru", "style_buddy") in label  # the current voice shows on the button


def test_settings_covers_every_preference_including_language():
    # /settings is the one panel now — language no longer has its own menu slot.
    kb = settings_keyboard("ru", 9, 180, style.FORTUNE)
    assert {"set:hour", "set:tz", "set:style", "set:lang"} <= set(_datas(kb))
    label = [b.text for row in kb.inline_keyboard for b in row if b.callback_data == "set:lang"][0]
    assert t("ru", "lang_name") in label  # shows the current language


def test_the_settings_panel_is_not_titled_after_reminders_alone():
    for lang in LANGS:
        title = t(lang, "settings_title", state="…")
        assert "{state}" not in title
        for word in ("reminder</b>", "напоминание</b>", "нагадування</b>"):
            assert word.lower() not in title.lower(), f"{lang} title still names only reminders"


def test_the_chosen_voice_survives_a_round_trip(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    try:
        db.get_or_create_user(1, "ru")
        # a user predating the column reads as the default, not as None
        assert asyncio.run(user_style(db, 1)) == style.DEFAULT
        db.set_style(1, style.PSY)
        assert asyncio.run(user_style(db, 1)) == style.PSY
        # ...and a stranger is unaffected
        assert asyncio.run(user_style(db, 999)) == style.DEFAULT
    finally:
        db.close()


def test_the_style_column_is_added_to_a_pre_existing_database(tmp_path):
    import sqlite3

    path = str(tmp_path / "old.db")
    # a database shaped like the one on the Fly volume before this feature
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, lang TEXT, created_at TEXT)")
    old.execute("INSERT INTO users VALUES (7, 'ru', '2026-01-01')")
    old.commit()
    old.close()

    db = Database(path)  # _migrate must ALTER, not fail
    try:
        assert db.get_style(7) is None
        assert asyncio.run(user_style(db, 7)) == style.DEFAULT
        db.set_style(7, style.BUDDY)
        assert db.get_style(7) == style.BUDDY
    finally:
        db.close()
