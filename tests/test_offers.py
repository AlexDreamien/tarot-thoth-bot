import asyncio

from bot import pricing
from bot.db import Database
from bot.keyboards import offers_keyboard
from bot.service import available_addons, spread_addon_state


def _datas(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def _spread(db):
    return db.get_or_create_spread(user_id=1, day="d", kind="daily", scope_key="k", card_ids=["a"])


def test_available_addons_tiers():
    assert available_addons(False, "none") == [
        pricing.FUTURE,
        pricing.EXTRA_2,
        pricing.EXTRA_5,
    ]
    # future bought → only the clarifying-card options
    assert available_addons(True, "none") == [pricing.EXTRA_2, pricing.EXTRA_5]
    # two clarifying cards → offer the +3 top-up, NOT +2 or +5
    assert available_addons(False, "two") == [pricing.FUTURE, pricing.EXTRA_3]
    # five clarifying cards → no clarifying-card buttons at all
    assert available_addons(False, "full") == [pricing.FUTURE]
    assert available_addons(True, "full") == []


def test_state_transitions_via_topup(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    try:
        sid = _spread(db)["id"]
        assert asyncio.run(spread_addon_state(db, sid)) == (False, "none")
        db.set_future(sid, "future")
        assert asyncio.run(spread_addon_state(db, sid)) == (True, "none")
        db.get_or_create_extra(spread_id=sid, count=2, card_ids=["m", "n"])
        assert asyncio.run(spread_addon_state(db, sid)) == (True, "two")
        db.get_or_create_extra(spread_id=sid, count=3, card_ids=["p", "q", "r"])
        assert asyncio.run(spread_addon_state(db, sid)) == (True, "full")
    finally:
        db.close()


def test_state_direct_five(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    try:
        sid = _spread(db)["id"]
        db.get_or_create_extra(spread_id=sid, count=5, card_ids=["a", "b", "c", "d", "e"])
        assert asyncio.run(spread_addon_state(db, sid)) == (False, "full")
    finally:
        db.close()


def test_offers_keyboard_renders_available_then_context():
    kb = offers_keyboard("en", 7, [pricing.FUTURE, pricing.EXTRA_3])
    assert _datas(kb) == [f"buy:{pricing.FUTURE}:7", f"buy:{pricing.EXTRA_3}:7", "ctx"]
    # empty available → the "reading for a situation" button still shows
    assert _datas(offers_keyboard("en", 7, [])) == ["ctx"]
