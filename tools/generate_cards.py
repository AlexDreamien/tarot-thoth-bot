"""Generate the 78 bundled card images into ``assets/cards/``.

Run once (and commit the PNGs):

    python tools/generate_cards.py

The current art is procedural (see ``bot.cards_render.render_card``): legible
placeholder art with element colours, glyphs and card names. To ship real
Thoth-style art, generate 78 images with your image model of choice and drop
them in ``assets/cards/<card_id>.png`` (same filenames) — nothing else changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.cards_render import ASSET_DIR, render_card  # noqa: E402
from bot.deck import DECK  # noqa: E402


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for card in DECK:
        out = ASSET_DIR / f"{card.id}.png"
        render_card(card).save(out)
    print(f"Wrote {len(DECK)} cards to {ASSET_DIR}")


if __name__ == "__main__":
    main()
