import sqlite3

import pytest

from bot import premium
from bot.db import Database
from bot.i18n import LANGS, t
from bot.keyboards import premium_state, settings_keyboard


def _datas(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


# --- the rule -------------------------------------------------------------


def test_premium_runs_through_the_expiry_day_itself():
    assert premium.is_active("2026-08-05", "2026-08-05") is True  # the last day counts
    assert premium.is_active("2026-08-05", "2026-08-04") is True
    assert premium.is_active("2026-08-05", "2026-08-06") is False


def test_no_date_means_no_premium():
    # NULL is the default for anyone who signs up after the grandfathering.
    assert premium.is_active(None, "2026-08-05") is False
    assert premium.is_active("", "2026-08-05") is False


def test_a_malformed_date_never_grants_premium():
    # Fail closed: a bad value must not read as "valid forever".
    for junk in ("forever", "2026-13-99", "05.08.2026", "2026"):
        assert premium.normalize(junk) is None
        assert premium.is_active(junk, "2026-08-05") is False


def test_normalize_keeps_the_sortable_form():
    assert premium.normalize("2099-01-01") == "2099-01-01"
    assert premium.normalize(None) is None


# --- what /settings shows -------------------------------------------------


def test_the_button_shows_the_date_while_active_and_says_so_when_not():
    label = premium_state("ru", "2099-01-01", "2026-08-05")
    assert "2099-01-01" in label
    assert premium_state("ru", None, "2026-08-05") == t("ru", "premium_off")
    assert premium_state("ru", "2026-01-01", "2026-08-05") == t("ru", "premium_off")


def test_settings_offers_the_premium_button():
    kb = settings_keyboard("ru", 9, 180, None, premium_until="2099-01-01", today="2026-08-05")
    assert "premium" in _datas(kb)
    label = [b.text for row in kb.inline_keyboard for b in row if b.callback_data == "premium"][0]
    assert "2099-01-01" in label


def test_every_language_has_the_premium_strings():
    for lang in LANGS:
        for key in ("btn_premium", "premium_on", "premium_off"):
            assert t(lang, key) != key, f"{lang}/{key}"
        assert "{date}" not in t(lang, "premium_title_on", date="2099-01-01")
        assert t(lang, "premium_title_off").strip()


# --- persistence and the one-time grandfathering --------------------------


@pytest.fixture()
def db(tmp_path):
    d = Database(str(tmp_path / "t.db"))
    yield d
    d.close()


def test_a_fresh_signup_gets_no_premium(db):
    # The backfill runs when the column appears; users created afterwards are
    # not silently handed a subscription.
    db.get_or_create_user(1, "ru")
    assert db.get_premium_until(1) is None
    assert premium.is_active(db.get_premium_until(1), "2026-08-05") is False


def test_premium_can_be_granted_and_revoked(db):
    db.get_or_create_user(1, "ru")
    db.set_premium_until(1, "2099-01-01")
    assert db.get_premium_until(1) == "2099-01-01"
    db.set_premium_until(1, None)
    assert db.get_premium_until(1) is None


def test_existing_users_are_grandfathered_in_when_the_column_appears(tmp_path):
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, lang TEXT, created_at TEXT)")
    old.executemany(
        "INSERT INTO users VALUES (?,?,?)", [(7, "ru", "2026-01-01"), (8, "ru", "2026-01-02")]
    )
    old.commit()
    old.close()

    d = Database(path)
    try:
        assert d.get_premium_until(7) == premium.GRANDFATHER_UNTIL
        assert d.get_premium_until(8) == premium.GRANDFATHER_UNTIL
        # ...and the grant does not re-run over someone whose premium was revoked
        d.set_premium_until(7, None)
    finally:
        d.close()

    again = Database(path)  # reopening re-runs _migrate
    try:
        assert again.get_premium_until(7) is None, "the backfill fired a second time"
        assert again.get_premium_until(8) == premium.GRANDFATHER_UNTIL
    finally:
        again.close()
