import pytest

from bot import memory
from bot.db import Database


def past(day, cards, kind="daily", situation=None, extra=None):
    """A row shaped like db.recent_readings returns."""
    return {
        "day": day,
        "kind": kind,
        "situation": situation,
        "card_ids": ",".join(cards),
        "extra_card_ids": ",".join(extra) if extra else None,
    }


def test_a_first_time_querent_gets_no_memory_block():
    # Nothing to remember must produce nothing at all — an empty preamble would
    # invite the model to gesture at a past that doesn't exist.
    assert memory.render_block([], ["major_16"], "ru", today="2026-08-05") == ""


def test_clarifying_cards_count_as_having_been_on_the_table():
    rows = [past("2026-08-01", ["major_00"], extra=["major_16", "cups_02"])]
    reading = memory.from_rows(rows)[0]
    assert reading.card_ids == ("major_00", "major_16", "cups_02")


def test_a_returning_card_is_reported_with_its_last_appearance():
    rows = [
        past("2026-08-03", ["cups_02", "swords_05", "disks_03"]),
        past("2026-07-22", ["major_16", "wands_04", "cups_09"], kind="context", situation="работа"),
        past("2026-07-10", ["major_16", "disks_07", "swords_02"]),
    ]
    block = memory.render_block(
        memory.from_rows(rows), ["major_16", "disks_05", "wands_02"], "ru", today="2026-08-05"
    )
    assert "Башня" in block
    assert "3rd time" in block  # twice before + today
    assert "2026-07-22" in block
    assert "14 days ago" in block
    assert "работа" in block  # the question it stood over last time


def test_cards_never_drawn_before_are_not_echoed():
    rows = [past("2026-08-01", ["cups_02"])]
    block = memory.render_block(memory.from_rows(rows), ["major_16"], "en", today="2026-08-05")
    assert "drawn before" not in block
    assert "Two of Cups" in block  # the recent-readings list still lists it


def test_echoes_are_ordered_by_persistence_then_recency():
    rows = [
        past("2026-08-04", ["cups_02"]),
        past("2026-08-01", ["major_16"]),
        past("2026-07-01", ["major_16"]),
    ]
    ech = memory.echoes(memory.from_rows(rows), ["cups_02", "major_16"])
    assert [e.card_id for e in ech] == ["major_16", "cups_02"]
    assert ech[0].times == 2
    assert ech[0].last_day == "2026-08-01"  # newest-first input ⇒ first hit is latest


def test_only_the_named_window_is_listed_but_the_whole_scan_is_searched():
    rows = [past(f"2026-06-{d:02d}", ["cups_02"]) for d in range(20, 8, -1)]
    block = memory.render_block(memory.from_rows(rows), ["cups_02"], "en", today="2026-06-21")
    listed = [ln for ln in block.splitlines() if ln.startswith("- 2026-06-")]
    assert len(listed) == memory.MAX_RECENT
    # ...yet the echo counts every one of the 12 readings, not just the 6 shown
    assert f"{len(rows) + 1}th time" in block


def test_a_long_question_is_trimmed():
    rows = [past("2026-08-01", ["cups_02"], kind="context", situation="я " * 400)]
    block = memory.render_block(memory.from_rows(rows), ["cups_02"], "ru", today="2026-08-05")
    assert "…" in block
    assert max(len(line) for line in block.splitlines()) < 300


def test_relative_dates_are_spelled_out_for_the_model():
    rows = [past("2026-08-04", ["cups_02"]), past("2026-08-05", ["swords_05"])]
    block = memory.render_block(memory.from_rows(rows), [], "en", today="2026-08-05")
    assert "yesterday" in block
    assert "earlier today" in block


def test_card_names_follow_the_querents_language():
    rows = [past("2026-08-01", ["major_16"])]
    assert "Башня" in memory.render_block(memory.from_rows(rows), [], "ru", today="2026-08-05")
    assert "The Tower" in memory.render_block(memory.from_rows(rows), [], "en", today="2026-08-05")


def test_ordinals_read_naturally():
    assert [memory._ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22)] == [
        "1st",
        "2nd",
        "3rd",
        "4th",
        "11th",
        "12th",
        "13th",
        "21st",
        "22nd",
    ]


# --- the DB side: whose history reaches the prompt -------------------------


@pytest.fixture()
def db(tmp_path):
    d = Database(str(tmp_path / "t.db"))
    yield d
    d.close()


def _spread(db, user_id, day, cards, *, kind="daily", read=True, situation=None):
    row = db.get_or_create_spread(
        user_id=user_id,
        day=day,
        kind=kind,
        scope_key=f"{user_id}:{day}:{kind}:{','.join(cards)}",
        card_ids=cards,
        situation=situation,
    )
    if read:
        db.set_interpretation(row["id"], "…")
    return row


def test_recent_readings_never_leak_across_users(db):
    _spread(db, 1, "2026-08-01", ["major_16"])
    _spread(db, 2, "2026-08-01", ["cups_02"])
    rows = db.recent_readings(1, 10)
    assert [r["card_ids"] for r in rows] == ["major_16"]


def test_recent_readings_skip_the_spread_being_read_right_now(db):
    _spread(db, 1, "2026-08-01", ["major_16"])
    today = _spread(db, 1, "2026-08-05", ["cups_02"], read=False)
    rows = db.recent_readings(1, 10, today["id"])
    assert [r["card_ids"] for r in rows] == ["major_16"]


def test_a_drawn_but_unread_spread_is_not_history(db):
    # The querent never saw it, so the reader can't remember it.
    _spread(db, 1, "2026-08-01", ["major_16"], read=False)
    assert db.recent_readings(1, 10) == []


def test_recent_readings_are_newest_first_and_carry_extras(db):
    old = _spread(db, 1, "2026-07-01", ["major_16"])
    db.get_or_create_extra(spread_id=old["id"], count=2, card_ids=["cups_02", "swords_05"])
    _spread(db, 1, "2026-08-01", ["disks_03"], kind="context", situation="работа")
    rows = db.recent_readings(1, 10)
    assert [r["day"] for r in rows] == ["2026-08-01", "2026-07-01"]
    assert rows[0]["situation"] == "работа"
    assert rows[1]["extra_card_ids"] == "cups_02,swords_05"
    assert rows[0]["extra_card_ids"] is None
