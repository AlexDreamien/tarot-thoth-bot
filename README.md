# Tarot Thoth Bot

A Telegram bot that draws a daily **three-card Thoth spread** (Crowley–Harris
deck) and interprets the querent's **current disposition** — where they stand
right now. Deliberately **not** fortune-telling: the free daily reading is a
sober, concrete explanation of the situation as the cards describe it.

- **One spread per day, fixed.** The cards and their interpretation are drawn
  and generated once per (user, day) and cached — they don't change until local
  midnight.
- **Multilingual** — Russian, Ukrainian, English, switchable with `/lang`.
- **Readings by Claude** (Opus 4.8) via the Anthropic API.
- **Card images** composited from bundled per-card art.
- **Paid add-ons** via Telegram Stars ⭐ (see below).

## Paid add-ons (Telegram Stars)

Offered after a spread:

| Add-on | What it does | Price |
|---|---|---|
| **Reading for a situation** | Describe a situation in words → a fresh three-card spread read specifically for it (current disposition, no prediction). | ⭐3 |
| **A look at the future** | Extends an existing spread with a forward-looking reading. | ⭐1 |
| **Two clarifying cards** | Adds 2 cards to a spread and reads them within it. | ⭐2 |
| **Five clarifying cards** | Adds 5 cards to a spread and reads them within it. | ⭐5 |

## Build & run

Requires Python 3.11+.

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in BOT_TOKEN, ANTHROPIC_API_KEY
python main.py
```

The Anthropic SDK reads `ANTHROPIC_API_KEY` from the environment. Configure the
model (`CLAUDE_MODEL`), the timezone that defines "today" (`TZ`), admin ids
(`ADMIN_IDS`, for `/stats`) and the SQLite path (`DB_PATH`) in `.env`.

## Card art

The 78 card images live in `assets/cards/<card_id>.png`. They are generated once
by:

```bash
python tools/generate_cards.py
```

The bundled art is an **original vector deck** drawn with Pillow: an
element-tinted gradient, a gilt double border, star-dust, classic pip layouts
for the small cards, heraldic medallions for the courts, and a bespoke symbol
for each Major Arcanum — one cohesive style, no third-party imagery. To ship a
different look (e.g. painterly art from an image model), drop 78 PNGs into
`assets/cards/` under the same filenames — nothing else changes. If an asset is
missing at runtime, the card is drawn on the fly by the same renderer.

## Tests & CI

```bash
pip install -r requirements-dev.txt
pytest
ruff check . && black --check .
```

Tests cover the pure core (deck, draws, day boundary, i18n, card names, DB
idempotency, prompt building). GitHub Actions runs ruff, black and pytest on
every push and pull request.

## Architecture

*Pure core + thin layer*, the same split as the sibling bots.

- **Core (aiogram/Pillow/network-free, unit-tested):** `bot/deck.py`,
  `bot/card_names.py`, `bot/daily.py`, `bot/db.py`, `bot/i18n.py`,
  `bot/pricing.py`, `bot/config.py`, and the prompt-building functions in
  `bot/interpret.py`.
- **Thin layer (not unit-tested):** `bot/handlers/`, `bot/service.py`,
  `bot/cards_render.py`, `bot/keyboards.py`, `main.py`, and the `Interpreter`
  class (the Claude IO boundary).

`main.py` runs aiogram long polling; DB calls are wrapped in `asyncio.to_thread`
so the event loop is never blocked by SQLite.

## Out of scope (deliberate)

Not "missing features" — intentional limits:

- **No fortune-telling in the free/context readings.** Only the paid "future"
  add-on looks ahead. This is the product's whole premise.
- **No reversed cards** — a spread reads upright only.
- **One deck (Thoth).** No deck selection.
- **No per-user timezone** — "today" is the configured `TZ` for everyone.
- **No web dashboard.**

## License / credits

[MIT](LICENSE). The deck *data* (card names and Thoth titles) is factual. The
bundled card art is original procedural work — **no third-party Thoth scans are
included**. If you replace it with copyrighted deck imagery, that is on the
deployer, not this repository.
