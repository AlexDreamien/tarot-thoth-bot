from bot.i18n import LANGS, MONTHS, WEEKDAYS
from bot.keyboards import calendar_keyboard, day_readings_keyboard


def _datas(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def test_calendar_labels_complete():
    for lang in LANGS:
        assert len(MONTHS[lang]) == 12
        assert len(WEEKDAYS[lang]) == 7


def test_calendar_marks_days_and_navigates():
    datas = _datas(calendar_keyboard(2026, 7, {20, 22}, "ru"))
    assert "hist:nav:2026-06" in datas  # ◀ previous month
    assert "hist:nav:2026-08" in datas  # ▶ next month
    assert "hist:day:2026-07-20" in datas  # marked days tappable
    assert "hist:day:2026-07-22" in datas
    assert "hist:day:2026-07-21" not in datas  # unmarked days are inert


def test_calendar_wraps_year_boundary():
    datas = _datas(calendar_keyboard(2026, 12, set(), "en"))
    assert "hist:nav:2027-01" in datas
    assert "hist:nav:2026-11" in datas


def test_day_readings_keyboard_lists_and_backs():
    rows = [
        {"id": 7, "kind": "daily", "situation": None, "day": "2026-07-22"},
        {"id": 8, "kind": "context", "situation": "job change", "day": "2026-07-22"},
    ]
    datas = _datas(day_readings_keyboard(rows, "en"))
    assert datas == ["hist:show:7", "hist:show:8", "hist:nav:2026-07"]
