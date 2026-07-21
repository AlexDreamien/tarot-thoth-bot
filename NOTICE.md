# NOTICE

Tarot Thoth Bot — Copyright (c) 2026 Alex Dreamien. Licensed under the MIT
License (see `LICENSE`).

## Deck data

The card set modelled in `bot/deck.py` — the 78 cards of the Thoth Tarot, their
Major Arcana names, suit/court structure and the esoteric titles of the pip
cards (e.g. "Dominion", "Ruin") — is **factual reference data** describing a
well-known tarot system (the Thoth Tarot conceived by Aleister Crowley and
painted by Lady Frieda Harris). Facts and short titles are not themselves a
creative work bundled from a third party.

## Card imagery

The card images in `assets/cards/` are **original procedural artwork** produced
by `tools/generate_cards.py` (Pillow — element colours, geometric emblems, card
names and titles). **No scans, photographs or reproductions of the Thoth deck
paintings — or of any other published tarot deck — are included in this
repository.**

The original Thoth Tarot artwork by Lady Frieda Harris may remain under
copyright in some jurisdictions. If you replace the bundled placeholder art with
copyrighted deck imagery, obtaining the necessary rights is the responsibility
of the deployer, not of this project.

## Readings

Interpretations are generated at runtime by Anthropic's Claude API from prompts
in `bot/interpret.py`. They are not bundled content and are not stored in this
repository.

## Third-party software

This project depends on open-source packages (aiogram, the Anthropic SDK,
Pillow, python-dotenv and their transitive dependencies), each distributed under
its own license. See each package's distribution for its terms.
