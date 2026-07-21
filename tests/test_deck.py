import pytest

from bot import deck


def test_deck_has_78_unique_cards():
    assert len(deck.DECK) == 78
    ids = [c.id for c in deck.DECK]
    assert len(set(ids)) == 78


def test_composition_22_majors_56_minors():
    majors = [c for c in deck.DECK if c.kind == "major"]
    minors = [c for c in deck.DECK if c.kind == "minor"]
    assert len(majors) == 22
    assert len(minors) == 56
    # 14 cards per suit
    for suit in deck.SUITS:
        assert len([c for c in minors if c.suit == suit]) == 14


def test_get_card_roundtrip():
    for c in deck.DECK:
        assert deck.get_card(c.id) is c
    with pytest.raises(KeyError):
        deck.get_card("nope_99")


def test_draw_is_deterministic_and_distinct():
    a = deck.draw("user:2026-01-01:daily", 3)
    b = deck.draw("user:2026-01-01:daily", 3)
    assert a == b
    assert len(set(a)) == 3
    # different key → (almost surely) different cards
    c = deck.draw("user:2026-01-02:daily", 3)
    assert a != c


def test_draw_prefix_property():
    # First N of a larger draw for the same key is a prefix of a smaller draw,
    # so a +2 and a +5 clarification off one parent share their first two cards.
    key = "spread-42:extra"
    two = deck.draw(key, 2)
    five = deck.draw(key, 5)
    assert five[:2] == two


def test_draw_excludes():
    base = deck.draw("k:daily", 3)
    extra = deck.draw("k:extra:2", 2, exclude=tuple(base))
    assert set(extra).isdisjoint(base)


def test_draw_overflow_raises():
    with pytest.raises(ValueError):
        deck.draw("k", 79)
    with pytest.raises(ValueError):
        deck.draw("k", 5, exclude=tuple(c.id for c in deck.DECK[:74]))
