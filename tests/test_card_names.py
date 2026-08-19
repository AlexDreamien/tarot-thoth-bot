from bot import deck
from bot.card_names import LANGS, card_name, card_title


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


def test_every_pip_has_a_title_in_every_language():
    for card in deck.DECK:
        for lang in LANGS:
            title = card_title(card, lang)
            # Majors and courts have no Thoth title; every pip has one everywhere
            assert (title is None) == (card.title is None)
            if title is not None:
                assert title.strip()


def test_titles_are_localized_and_english_stays_canonical():
    cruelty = deck.get_card("swords_09")
    assert card_title(cruelty, "en") == "Cruelty"
    assert card_title(cruelty, "ru") == "Жестокость"
    assert card_title(cruelty, "uk") == "Жорстокість"
    assert card_title(cruelty, "fr") == "Cruelty"  # unknown language → the original
    assert card_title(deck.get_card("cups_queen"), "ru") is None
