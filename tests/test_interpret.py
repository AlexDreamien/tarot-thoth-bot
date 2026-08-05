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


def test_memory_rules_are_absent_until_there_is_a_history():
    # A first-time querent's prompt must be byte-identical to the old one — no
    # dangling instructions about readings that don't exist.
    assert interpret.system_prompt("ru") == interpret.system_prompt("ru", memory=False)
    assert "earlier readings" not in interpret.system_prompt("ru")


def test_memory_rules_forbid_inventing_a_past():
    sys = interpret.system_prompt("ru", memory=True).lower()
    assert "earlier readings" in sys
    assert "never mention a reading, card or date that is not in that list" in sys
    assert "one short clause" in sys  # a brief reading stays brief


def test_memory_block_rides_in_the_reading_prompt():
    block = "This querent's own earlier readings:\n- 2026-07-22: Башня"
    prompt = interpret.build_daily_user(["major_16"], "ru", block)
    assert block in prompt
    # the instruction to interpret still comes last
    assert prompt.rstrip().endswith("current disposition.")
    assert interpret.build_daily_user(["major_16"], "ru", "") == interpret.build_daily_user(
        ["major_16"], "ru"
    )


def test_context_prompt_carries_memory_too():
    prompt = interpret.build_context_user(["cups_02"], "смена работы", "ru", "ПАМЯТЬ")
    assert "смена работы" in prompt
    assert "ПАМЯТЬ" in prompt


def test_extra_user_references_base_and_extra():
    prompt = interpret.build_extra_user(
        ["major_01"], "the base reading", ["swords_10", "disks_03"], "en"
    )
    assert "the base reading" in prompt
    assert "2 clarifying cards" in prompt
    assert "Ruin" in prompt  # Thoth title of the 10 of Swords
