from bot import deck
from bot.card_names import LANGS, card_name


def test_every_card_has_a_name_in_every_language():
    for card in deck.DECK:
        for lang in LANGS:
            name = card_name(card, lang)
            assert name and isinstance(name, str)


def test_english_minor_uses_of_connector():
    ace = deck.get_card("wands_01")
    assert card_name(ace, "en") == "Ace of Wands"
    assert card_name(ace, "ru") == "Туз Жезлов"


def test_major_localized():
    fool = deck.get_card("major_00")
    assert card_name(fool, "en") == "The Fool"
    assert card_name(fool, "ru") == "Шут"
    assert card_name(fool, "uk") == "Дурень"


def test_unknown_lang_falls_back_to_english():
    card = deck.get_card("cups_queen")
    assert card_name(card, "fr") == card_name(card, "en")
