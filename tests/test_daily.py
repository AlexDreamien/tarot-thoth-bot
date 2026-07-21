from datetime import UTC, datetime

from bot.daily import day_key


def test_day_key_format():
    now = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
    assert day_key("Europe/Kyiv", now) == "2026-07-21"


def test_day_key_respects_timezone_boundary():
    # 23:30 UTC is already the next day in Kyiv (UTC+3 in July).
    now = datetime(2026, 7, 21, 23, 30, tzinfo=UTC)
    assert day_key("Europe/Kyiv", now) == "2026-07-22"
    # ...but still the 21st in New York.
    assert day_key("America/New_York", now) == "2026-07-21"
