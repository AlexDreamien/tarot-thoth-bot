"""Localized display names for Thoth cards (ru / uk / en).

Pure core, unit-tested. Minor-card names are composed from a rank word, a
language-specific connector and a suit word, so we translate ~40 tokens per
language instead of 78 full names. These are the *display* names (message
header, image fallback); the model-facing canonical English names live in
``deck.Card.name`` and may differ stylistically (e.g. display "Two of Wands"
vs. canonical "2 of Wands").

The Claude interpretation is written in the querent's language and names the
cards itself; these localized names ensure a ru/uk player never sees a bare
English name in the header.
"""

from __future__ import annotations

from .deck import Card

LANGS = ("ru", "uk", "en")

# Major Arcana names, per language, indexed 0..21 (trump order).
_MAJOR_NAMES = {
    "en": [
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
    ],
    "ru": [
        "Шут",
        "Маг",
        "Жрица",
        "Императрица",
        "Император",
        "Иерофант",
        "Влюблённые",
        "Колесница",
        "Равновесие",
        "Отшельник",
        "Фортуна",
        "Вожделение",
        "Повешенный",
        "Смерть",
        "Искусство",
        "Дьявол",
        "Башня",
        "Звезда",
        "Луна",
        "Солнце",
        "Эон",
        "Вселенная",
    ],
    "uk": [
        "Дурень",
        "Маг",
        "Жриця",
        "Імператриця",
        "Імператор",
        "Ієрофант",
        "Закохані",
        "Колісниця",
        "Рівновага",
        "Самітник",
        "Фортуна",
        "Жага",
        "Повішений",
        "Смерть",
        "Мистецтво",
        "Диявол",
        "Вежа",
        "Зірка",
        "Місяць",
        "Сонце",
        "Еон",
        "Всесвіт",
    ],
}

# Suit names in the genitive-of-suit sense ("... of Wands").
_SUIT_NAMES = {
    "en": {"wands": "Wands", "cups": "Cups", "swords": "Swords", "disks": "Disks"},
    "ru": {"wands": "Жезлов", "cups": "Кубков", "swords": "Мечей", "disks": "Дисков"},
    "uk": {"wands": "Жезлів", "cups": "Келихів", "swords": "Мечів", "disks": "Дисків"},
}

# Connector between rank and suit ("Two of Wands" vs "Двойка Жезлов").
_CONNECTOR = {"en": " of ", "ru": " ", "uk": " "}

# Rank words. Pip ranks keyed by int 1..10; court ranks by their code.
_RANK_NAMES = {
    "en": {
        1: "Ace",
        2: "Two",
        3: "Three",
        4: "Four",
        5: "Five",
        6: "Six",
        7: "Seven",
        8: "Eight",
        9: "Nine",
        10: "Ten",
        "knight": "Knight",
        "queen": "Queen",
        "prince": "Prince",
        "princess": "Princess",
    },
    "ru": {
        1: "Туз",
        2: "Двойка",
        3: "Тройка",
        4: "Четвёрка",
        5: "Пятёрка",
        6: "Шестёрка",
        7: "Семёрка",
        8: "Восьмёрка",
        9: "Девятка",
        10: "Десятка",
        "knight": "Рыцарь",
        "queen": "Королева",
        "prince": "Принц",
        "princess": "Принцесса",
    },
    "uk": {
        1: "Туз",
        2: "Двійка",
        3: "Трійка",
        4: "Четвірка",
        5: "П'ятірка",
        6: "Шістка",
        7: "Сімка",
        8: "Вісімка",
        9: "Дев'ятка",
        10: "Десятка",
        "knight": "Лицар",
        "queen": "Королева",
        "prince": "Принц",
        "princess": "Принцеса",
    },
}


# Thoth esoteric titles of the small cards, per language, indexed 1..10 — the
# same order as ``deck._PIP_TITLES``, which holds Crowley's English originals.
# These go into the *prompt*: given only the English title the model quotes it
# verbatim in a Russian reading («Девятка Мечей, „Cruelty“, задаёт тон»).
_PIP_TITLES = {
    "ru": {
        "wands": [
            "Корень Сил Огня",
            "Господство",
            "Добродетель",
            "Завершение",
            "Раздор",
            "Победа",
            "Доблесть",
            "Быстрота",
            "Сила",
            "Угнетение",
        ],
        "cups": [
            "Корень Сил Воды",
            "Любовь",
            "Изобилие",
            "Роскошь",
            "Разочарование",
            "Удовольствие",
            "Разврат",
            "Праздность",
            "Счастье",
            "Пресыщение",
        ],
        "swords": [
            "Корень Сил Воздуха",
            "Мир",
            "Печаль",
            "Перемирие",
            "Поражение",
            "Наука",
            "Тщетность",
            "Вмешательство",
            "Жестокость",
            "Крушение",
        ],
        "disks": [
            "Корень Сил Земли",
            "Перемена",
            "Труд",
            "Власть",
            "Беспокойство",
            "Успех",
            "Неудача",
            "Благоразумие",
            "Прибыль",
            "Богатство",
        ],
    },
    "uk": {
        "wands": [
            "Корінь Сил Вогню",
            "Панування",
            "Чеснота",
            "Завершення",
            "Чвари",
            "Перемога",
            "Доблесть",
            "Швидкість",
            "Сила",
            "Гноблення",
        ],
        "cups": [
            "Корінь Сил Води",
            "Любов",
            "Достаток",
            "Розкіш",
            "Розчарування",
            "Насолода",
            "Розпуста",
            "Лінощі",
            "Щастя",
            "Пересичення",
        ],
        "swords": [
            "Корінь Сил Повітря",
            "Мир",
            "Скорбота",
            "Перемир'я",
            "Поразка",
            "Наука",
            "Марність",
            "Втручання",
            "Жорстокість",
            "Крах",
        ],
        "disks": [
            "Корінь Сил Землі",
            "Зміна",
            "Праця",
            "Влада",
            "Тривога",
            "Успіх",
            "Невдача",
            "Розважливість",
            "Прибуток",
            "Багатство",
        ],
    },
}


def card_title(card: Card, lang: str) -> str | None:
    """The card's Thoth title in ``lang``, or None for a card that has none
    (Majors and courts). English — and any language we have no titles for —
    falls back to Crowley's original in ``deck.Card.title``."""
    if not card.title:
        return None
    per_suit = _PIP_TITLES.get(lang)
    if per_suit is None:
        return card.title
    return per_suit[card.suit][card.rank - 1]


def card_name(card: Card, lang: str) -> str:
    """Localized display name for a card. Falls back to English for an unknown
    language."""
    if lang not in LANGS:
        lang = "en"
    if card.kind == "major":
        return _MAJOR_NAMES[lang][card.number]
    rank_word = _RANK_NAMES[lang][card.rank]
    suit_word = _SUIT_NAMES[lang][card.suit]
    return f"{rank_word}{_CONNECTOR[lang]}{suit_word}"
