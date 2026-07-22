import asyncio

from bot import pricing
from bot.db import Database
from bot.keyboards import offers_keyboard
from bot.service import purchased_addons


def _datas(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def test_purchased_addons_tracks_future_and_extras(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    try:
        row = db.get_or_create_spread(
            user_id=1, day="d", kind="daily", scope_key="k", card_ids=["a"]
        )
        sid = row["id"]
        assert asyncio.run(purchased_addons(db, sid)) == set()

        db.set_future(sid, "the future")
        db.get_or_create_extra(spread_id=sid, count=2, card_ids=["m", "n"])
        assert asyncio.run(purchased_addons(db, sid)) == {pricing.FUTURE, pricing.EXTRA_2}
    finally:
        db.close()


def test_offers_hide_bought_addons_but_always_keep_context():
    # Nothing bought → all three add-ons + context.
    assert _datas(offers_keyboard("en", 1)) == [
        f"buy:{pricing.FUTURE}:1",
        f"buy:{pricing.EXTRA_2}:1",
        f"buy:{pricing.EXTRA_5}:1",
        "ctx",
    ]
    # future + two-cards bought → only five-cards and context remain.
    assert _datas(offers_keyboard("en", 1, {pricing.FUTURE, pricing.EXTRA_2})) == [
        f"buy:{pricing.EXTRA_5}:1",
        "ctx",
    ]
    # Everything bought → the "reading for a situation" button always stays.
    everything = {pricing.FUTURE, pricing.EXTRA_2, pricing.EXTRA_5}
    assert _datas(offers_keyboard("en", 1, everything)) == ["ctx"]
