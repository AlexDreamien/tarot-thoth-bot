from bot import interpret


def test_system_prompt_enforces_no_prediction():
    sys = interpret.system_prompt("ru")
    assert "current disposition" in sys.lower()
    assert "do not predict" in sys.lower()
    assert "русском" in sys


def test_future_system_prompt_is_forward_looking():
    sys = interpret.future_system_prompt("en")
    assert "ahead" in sys.lower()


def test_daily_user_lists_the_cards():
    prompt = interpret.build_daily_user(["major_00", "wands_02"], "en")
    assert "The Fool" in prompt
    assert "Dominion" in prompt  # Thoth title of the 2 of Wands


def test_context_user_includes_situation():
    prompt = interpret.build_context_user(["cups_02"], "смена работы", "ru")
    assert "смена работы" in prompt
    assert "Двойка Кубков" in prompt  # localized name grounds the reading


def test_extra_user_references_base_and_extra():
    prompt = interpret.build_extra_user(
        ["major_01"], "the base reading", ["swords_10", "disks_03"], "en"
    )
    assert "the base reading" in prompt
    assert "2 clarifying cards" in prompt
    assert "Ruin" in prompt  # Thoth title of the 10 of Swords
