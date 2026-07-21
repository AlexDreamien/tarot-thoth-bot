import pytest

from bot.db import Database, split_cards


@pytest.fixture()
def db(tmp_path):
    d = Database(str(tmp_path / "t.db"))
    yield d
    d.close()


def test_user_lifecycle(db):
    assert db.get_lang(1) is None
    assert db.get_or_create_user(1, "ru") == "ru"
    # second call keeps the stored lang, ignores the new default
    assert db.get_or_create_user(1, "en") == "ru"
    db.set_lang(1, "uk")
    assert db.get_lang(1) == "uk"


def test_spread_is_idempotent(db):
    kwargs = dict(
        user_id=1,
        day="2026-01-01",
        kind="daily",
        scope_key="1:2026-01-01:daily",
        card_ids=["major_00", "cups_02", "disks_10"],
    )
    row1 = db.get_or_create_spread(**kwargs)
    # a racing/retried draw with different cards must not replace the stored one
    row2 = db.get_or_create_spread(**{**kwargs, "card_ids": ["swords_05"]})
    assert row1["id"] == row2["id"]
    assert split_cards(row2["card_ids"]) == ["major_00", "cups_02", "disks_10"]


def test_interpretation_and_future(db):
    row = db.get_or_create_spread(
        user_id=1, day="d", kind="daily", scope_key="k", card_ids=["major_01"]
    )
    db.set_interpretation(row["id"], "current disposition")
    db.set_future(row["id"], "the future")
    fresh = db.get_spread(row["id"])
    assert fresh["interpretation"] == "current disposition"
    assert fresh["future_text"] == "the future"


def test_last_spread(db):
    db.get_or_create_spread(user_id=7, day="d", kind="daily", scope_key="a", card_ids=["x"])
    db.get_or_create_spread(user_id=7, day="d", kind="context", scope_key="b", card_ids=["y"])
    assert db.get_last_spread(7)["scope_key"] == "b"


def test_extra_is_idempotent(db):
    row = db.get_or_create_spread(user_id=1, day="d", kind="daily", scope_key="k", card_ids=["a"])
    e1 = db.get_or_create_extra(spread_id=row["id"], count=2, card_ids=["m", "n"])
    e2 = db.get_or_create_extra(spread_id=row["id"], count=2, card_ids=["p", "q"])
    assert e1["id"] == e2["id"]
    assert split_cards(e2["card_ids"]) == ["m", "n"]


def test_stats_and_purchases(db):
    db.get_or_create_user(1, "ru")
    db.get_or_create_spread(user_id=1, day="d", kind="daily", scope_key="k", card_ids=["a"])
    db.log_purchase(user_id=1, product="future", stars=1, charge_id="c1")
    db.log_purchase(user_id=1, product="extra_5", stars=5, charge_id="c2")
    s = db.stats()
    assert s == {"users": 1, "spreads": 1, "purchases": 2, "stars": 6}


def test_usable_from_another_thread(db):
    # The async layer calls db methods from asyncio.to_thread worker threads,
    # not the thread that opened the connection. Without check_same_thread=False
    # this raises sqlite3.ProgrammingError and every handler silently fails.
    import threading

    result: dict[str, object] = {}

    def worker():
        try:
            result["lang"] = db.get_or_create_user(99, "en")
        except Exception as e:  # noqa: BLE001
            result["error"] = e

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert result.get("error") is None, result.get("error")
    assert result["lang"] == "en"
