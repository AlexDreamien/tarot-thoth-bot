from bot.i18n import _STRINGS, LANGS, t


def test_all_languages_have_matching_keys():
    reference = set(_STRINGS["en"])
    for lang in LANGS:
        assert set(_STRINGS[lang]) == reference, f"{lang} key set differs"


def test_translation_and_formatting():
    assert "2026-07-21" in t("ru", "daily_header", date="2026-07-21")


def test_missing_key_falls_back_to_key_name():
    assert t("ru", "no_such_key_xyz") == "no_such_key_xyz"


def test_unknown_language_falls_back_to_default():
    assert t("fr", "cancelled") == t("ru", "cancelled")
