from bot import pricing


def test_prices():
    assert pricing.price(pricing.CONTEXT_READING) == 3
    assert pricing.price(pricing.FUTURE) == 1
    assert pricing.price(pricing.EXTRA_2) == 2
    assert pricing.price(pricing.EXTRA_5) == 5


def test_extra_counts_match_products():
    assert pricing.EXTRA_COUNT[pricing.EXTRA_2] == 2
    assert pricing.EXTRA_COUNT[pricing.EXTRA_5] == 5
