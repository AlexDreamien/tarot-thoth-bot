from datetime import UTC, datetime

from bot.keyboards import newday_keyboard
from bot.scheduler import bio_hint_due, due_reminders, local_now

TZ = "Europe/Kyiv"


def _u(uid, hour, offset=None, last=None, weekly=None):
    return {
        "user_id": uid,
        "reminder_hour": hour,
        "tz_offset_min": offset,
        "last_reminder_day": last,
        "last_weekly_day": weekly,
    }


def test_local_now_uses_offset_then_bot_tz():
    now = datetime(2026, 8, 3, 6, 5, tzinfo=UTC)
    assert local_now(now, 120, TZ).hour == 8  # UTC+2
    assert local_now(now, -300, TZ).hour == 1  # UTC-5
    assert local_now(now, None, TZ).hour == 9  # Kyiv is UTC+3 in August


def test_daily_fires_at_local_hour_only():
    now = datetime(2026, 8, 3, 6, 5, tzinfo=UTC)  # 09:05 Kyiv, 08:05 at UTC+2
    users = [_u(1, 9, None), _u(2, 9, 120), _u(3, 8, 120)]
    fired = {uid for uid, _, _ in due_reminders(users, now, TZ)}
    assert fired == {1, 3}  # user 2's local hour is 8, not 9


def test_daily_is_once_per_local_day():
    now = datetime(2026, 8, 3, 6, 5, tzinfo=UTC)
    assert due_reminders([_u(1, 9, None, last="2026-08-03")], now, TZ) == []
    assert due_reminders([_u(1, 9, None, last="2026-08-02")], now, TZ) != []


def test_outside_the_tick_window_nothing_fires():
    now = datetime(2026, 8, 3, 6, 35, tzinfo=UTC)  # 09:35 Kyiv — past the window
    assert due_reminders([_u(1, 9, None)], now, TZ) == []


def test_reminders_off_get_a_silent_weekly_nudge():
    now = datetime(2026, 8, 3, 10, 2, tzinfo=UTC)  # 13:02 Kyiv
    # never nudged → fires, silent
    out = due_reminders([_u(1, None, None)], now, TZ)
    assert out == [(1, "2026-08-03", True)]
    # nudged 3 days ago → too soon
    assert due_reminders([_u(1, None, None, weekly="2026-07-31")], now, TZ) == []
    # nudged 7 days ago → fires again
    assert due_reminders([_u(1, None, None, weekly="2026-07-27")], now, TZ) != []


def test_off_users_get_nothing_at_the_daily_hour():
    now = datetime(2026, 8, 3, 6, 5, tzinfo=UTC)  # 09:05 Kyiv
    assert due_reminders([_u(1, None, None)], now, TZ) == []


def _b(bio=None, last_hint=None):
    return {"bio": bio, "last_bio_hint_day": last_hint}


def test_bio_hint_only_for_a_querent_without_one():
    assert bio_hint_due(_b(), "2026-08-11") is True
    assert bio_hint_due(_b(bio="музыкант, 30 лет"), "2026-08-11") is False
    # a bio of nothing but whitespace is no bio at all
    assert bio_hint_due(_b(bio="   "), "2026-08-11") is True


def test_bio_hint_is_at_most_weekly():
    assert bio_hint_due(_b(last_hint="2026-08-08"), "2026-08-11") is False  # 3 days ago
    assert bio_hint_due(_b(last_hint="2026-08-04"), "2026-08-11") is True  # 7 days ago
    # …and a filled-in bio ends it regardless of when we last asked
    assert bio_hint_due(_b(bio="x", last_hint="2026-07-01"), "2026-08-11") is False


def test_bio_hint_adds_a_second_button_to_the_reminder():
    plain = newday_keyboard("ru").inline_keyboard
    hinted = newday_keyboard("ru", bio_hint=True).inline_keyboard
    assert len(plain) == 1 and len(hinted) == 2
    assert hinted[0] == plain[0]  # the new-day button stays first
    assert hinted[1][0].callback_data == "set:bio"
