"""The Thoth tarot deck (78 cards) and deterministic, seeded draws.

Pure, dependency-free core: no aiogram, no Pillow, no network. Everything here
is unit-tested. A card is identified by a stable string ``id`` that also names
its asset file (``assets/cards/<id>.png``).

Card identity is fixed forever — ids are persisted in the database and baked
into asset filenames, so never renumber or rename an existing card.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# --- Suits (Minor Arcana) -------------------------------------------------

SUITS = ("wands", "cups", "swords", "disks")
SUIT_ELEMENT = {
    "wands": "fire",
    "cups": "water",
    "swords": "air",
    "disks": "earth",
}

# Pip ranks 1..10 (1 = Ace) and the four Thoth court ranks.
PIP_RANKS = tuple(range(1, 11))
COURT_RANKS = ("knight", "queen", "prince", "princess")

# Thoth esoteric titles for the small (pip) cards, per suit, indexed 1..10.
_PIP_TITLES = {
    "wands": [
        "Root of the Powers of Fire",
        "Dominion",
        "Virtue",
        "Completion",
        "Strife",
        "Victory",
        "Valour",
        "Swiftness",
        "Strength",
        "Oppression",
    ],
    "cups": [
        "Root of the Powers of Water",
        "Love",
        "Abundance",
        "Luxury",
        "Disappointment",
        "Pleasure",
        "Debauch",
        "Indolence",
        "Happiness",
        "Satiety",
    ],
    "swords": [
        "Root of the Powers of Air",
        "Peace",
        "Sorrow",
        "Truce",
        "Defeat",
        "Science",
        "Futility",
        "Interference",
        "Cruelty",
        "Ruin",
    ],
    "disks": [
        "Root of the Powers of Earth",
        "Change",
        "Works",
        "Power",
        "Worry",
        "Success",
        "Failure",
        "Prudence",
        "Gain",
        "Wealth",
    ],
}

# Major Arcana with their Thoth names, in trump order 0..21.
_MAJORS = [
    "The Fool",
    "The Magus",
    "The Priestess",
    "The Empress",
    "The Emperor",
    "The Hierophant",
    "The Lovers",
    "The Chariot",
    "Adjustment",
    "The Hermit",
    "Fortune",
    "Lust",
    "The Hanged Man",
    "Death",
    "Art",
    "The Devil",
    "The Tower",
    "The Star",
    "The Moon",
    "The Sun",
    "The Aeon",
    "The Universe",
]

_ROMAN = [
    "0",
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
    "XIV",
    "XV",
    "XVI",
    "XVII",
    "XVIII",
    "XIX",
    "XX",
    "XXI",
]


@dataclass(frozen=True)
class Card:
    """One Thoth card. ``name`` is the canonical English name; localized names
    live in ``card_names``."""

    id: str
    kind: str  # "major" | "minor"
    name: str
    # Major-only:
    number: int | None = None  # 0..21
    roman: str | None = None
    # Minor-only:
    suit: str | None = None
    rank: object | None = None  # int 1..10 or a court-rank str
    element: str | None = None
    title: str | None = None  # Thoth esoteric title (pip cards)


def _build_deck() -> tuple[list[Card], dict[str, Card]]:
    cards: list[Card] = []

    for n, name in enumerate(_MAJORS):
        cards.append(Card(id=f"major_{n:02d}", kind="major", name=name, number=n, roman=_ROMAN[n]))

    court_names = {
        "knight": "Knight",
        "queen": "Queen",
        "prince": "Prince",
        "princess": "Princess",
    }
    for suit in SUITS:
        element = SUIT_ELEMENT[suit]
        suit_word = suit.capitalize()
        for rank in PIP_RANKS:
            title = _PIP_TITLES[suit][rank - 1]
            pip_word = "Ace" if rank == 1 else str(rank)
            name = f"{pip_word} of {suit_word}"
            cards.append(
                Card(
                    id=f"{suit}_{rank:02d}",
                    kind="minor",
                    name=name,
                    suit=suit,
                    rank=rank,
                    element=element,
                    title=title,
                )
            )
        for rank in COURT_RANKS:
            name = f"{court_names[rank]} of {suit_word}"
            cards.append(
                Card(
                    id=f"{suit}_{rank}",
                    kind="minor",
                    name=name,
                    suit=suit,
                    rank=rank,
                    element=element,
                )
            )

    by_id = {c.id: c for c in cards}
    return cards, by_id


DECK, _BY_ID = _build_deck()
assert len(DECK) == 78, f"Thoth deck must have 78 cards, got {len(DECK)}"


def get_card(card_id: str) -> Card:
    """Look up a card by id. Raises KeyError for an unknown id."""
    return _BY_ID[card_id]


def _seed(key: str) -> int:
    """Stable 64-bit seed from a string, independent of PYTHONHASHSEED."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def draw(key: str, count: int, exclude: tuple[str, ...] = ()) -> list[str]:
    """Deterministically draw ``count`` distinct card ids for ``key``.

    Same ``key`` always yields the same cards (the whole point: a spread is
    fixed for the day). ``exclude`` removes already-drawn ids so follow-up
    draws (extra clarifying cards) don't repeat the original spread.

    We use an incremental Fisher-Yates so that, for the same key, the first
    ``k`` cards of a larger draw are a prefix of a smaller draw — a +2 and a
    +5 clarification off the same parent share their first two cards.
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    excluded = set(exclude)
    pool = [c.id for c in DECK if c.id not in excluded]
    if count > len(pool):
        raise ValueError(f"cannot draw {count} cards from a pool of {len(pool)}")

    import random

    rng = random.Random(_seed(key))
    # Partial Fisher-Yates: pick `count` items from the front.
    for i in range(count):
        j = rng.randrange(i, len(pool))
        pool[i], pool[j] = pool[j], pool[i]
    return pool[:count]
