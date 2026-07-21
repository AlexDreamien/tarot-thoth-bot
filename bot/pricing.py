"""Telegram Stars (XTR) prices for the paid add-ons.

Pure constants. Amounts are in whole Stars (Telegram bills XTR in integer units;
one Star == amount 1 in the invoice's LabeledPrice).
"""

from __future__ import annotations

# Product codes — persisted in the purchases table and embedded in invoice
# payloads, so keep them stable.
CONTEXT_READING = "context_reading"
FUTURE = "future"
EXTRA_2 = "extra_2"
EXTRA_5 = "extra_5"

PRICES_STARS = {
    CONTEXT_READING: 3,  # describe a situation → a fresh 3-card spread for it
    FUTURE: 1,  # append a future-looking reading to a spread
    EXTRA_2: 2,  # two clarifying cards added to a spread
    EXTRA_5: 5,  # five clarifying cards added to a spread
}

# How many extra cards each "extra" product adds.
EXTRA_COUNT = {EXTRA_2: 2, EXTRA_5: 5}


def price(product: str) -> int:
    """Star price for a product code."""
    return PRICES_STARS[product]
