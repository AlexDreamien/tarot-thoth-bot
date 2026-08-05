# Tarot Thoth Bot

A Telegram bot that draws a daily **three-card Thoth spread** (Crowley–Harris
deck) and interprets the querent's **current disposition** — where they stand
right now. Deliberately **not** fortune-telling: the free daily reading is a
sober, concrete explanation of the situation as the cards describe it.

- **One spread per day, fixed.** The cards and their interpretation are drawn
  and generated once per (user, day) and cached — they don't change until local
  midnight.
- **Multilingual** — Russian, Ukrainian, English, switchable in `/settings`.
- **Readings by Claude** (Opus 4.8) via the Anthropic API.
- **Card images** composited from bundled per-card art.
- **Brief by default** — readings are a tight paragraph; an "expand this reading"
  button gives the full, detailed version of *any* reading (spread, future, or
  clarifying cards).
- **Four voices** (`/settings`) — fortune-teller (the default esoteric register),
  psychologist, logician, or blunt mate. The voice changes; the premise does not
  — every style reads the present and still refuses to predict.
- **Addressed how you like** (`/settings`) — set a gender and the readings agree
  with it; set a name and you'll be called by it now and then. Set neither and
  they're written without gendered wording rather than guessing.
- **Daily reminder** — an offer to draw, at an hour you choose in your own time
  zone (`/settings`). Turn it off and you still get one silent nudge a week.
- **The reader remembers you.** A reading is given your own recent spreads and
  questions, so when a card returns it says so — "the Tower again, three weeks
  after it stood over the same question" — instead of treating every day as the
  first. Strictly your own history; nothing crosses between querents.
- **Personal archive** — `/history` shows a calendar of your past readings to revisit.
- **Add-ons** offered after every spread (see below).

## Add-ons

Offered as buttons after a spread. They're **free by default**; set
`PAYMENTS_ENABLED=true` to sell them for Telegram Stars ⭐ instead (the price in
parentheses).

| Add-on | What it does | Stars |
|---|---|---|
| **Reading for a situation** | Describe a situation in words → a fresh three-card spread read specifically for it (current disposition, no prediction). Unlimited per day. | ⭐3 |
| **A look at the future** | Extends a spread with a forward-looking reading. Once per spread. | ⭐1 |
| **Clarifying cards** | Add cards to a spread and read them within it: +2 (⭐2) or +5 (⭐5); after a +2, a +3 top-up (⭐3) reaches five. Once each per spread. | ⭐2–5 |
| **Expand this reading** | The full, detailed version of a reading given briefly. Offered after every reading — spread, future, or clarifying cards. | ⭐1 |

Each add-on (future, clarifying cards) is once per spread; a context reading is a
fresh independent spread with its own add-ons.

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

## Exporting a user's readings

```bash
python tools/export_readings.py --list                 # who's in the database
python tools/export_readings.py 123456789              # full history
python tools/export_readings.py 123456789 --from 2026-08-01 --to 2026-08-31
```

The script downloads a fresh copy of the production database from the Fly
volume (`--no-fetch` reuses the last one, `--db` points at another file) and
writes `tools/readings_<user_id>[_<range>].txt` with each reading's date and
time, type, situation, cards, interpretation, future and clarifying draws. The
database copy and the exports are gitignored — they hold personal data.

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
  `bot/memory.py`, `bot/pricing.py`, `bot/style.py`, `bot/config.py`, and the
  prompt-building functions in `bot/interpret.py`.
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
- **Memory carries cards and questions, not past interpretations.** The prompt
  gets what was on the table and what was asked, never the old readings' text —
  signal over volume, and it keeps a reading from rewriting yesterday's.
- **No web dashboard.**

## License / credits

[MIT](LICENSE). The deck *data* (card names and Thoth titles) is factual. The
bundled card art is original procedural work — **no third-party Thoth scans are
included**. If you replace it with copyrighted deck imagery, that is on the
deployer, not this repository.
