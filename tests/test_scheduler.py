from datetime import UTC, datetime

from bot.scheduler import due_reminders, local_now

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
