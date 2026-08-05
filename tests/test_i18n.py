from bot.i18n import _STRINGS, LANGS, OFFERS_TITLES, offers_title, t


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


# --- the varied invitation above the action buttons -----------------------


def test_every_language_offers_the_same_number_of_variants():
    # OFFERS_TITLES lives outside _STRINGS, so the key-parity test above does
    # not cover it — a language left with one phrase would repeat forever.
    counts = {lang: len(OFFERS_TITLES[lang]) for lang in LANGS}
    assert len(set(counts.values())) == 1, f"uneven variant counts: {counts}"
    assert all(n >= 4 for n in counts.values())


def test_variants_are_distinct_and_non_empty():
    for lang in LANGS:
        variants = OFFERS_TITLES[lang]
        assert len(set(variants)) == len(variants), f"{lang} repeats a phrase"
        assert all(v.strip() for v in variants)


def test_the_index_picks_deterministically_and_wraps():
    variants = OFFERS_TITLES["ru"]
    assert offers_title("ru", 0) == variants[0]
    assert offers_title("ru", 3) == variants[3]
    assert offers_title("ru", len(variants)) == variants[0]  # wraps


def test_random_choice_covers_the_whole_set():
    seen = {offers_title("en") for _ in range(400)}
    assert seen == set(OFFERS_TITLES["en"])


def test_unknown_language_falls_back_to_the_default_variants():
    assert offers_title("fr", 2) == offers_title("ru", 2)
