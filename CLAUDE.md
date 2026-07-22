# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

Telegram bot for a daily **three-card Thoth tarot** reading (Crowley–Harris
deck, languages ru/uk/en). It draws a spread, generates a reading of the
querent's **current disposition** (not fortune-telling) via the Claude API,
composites the three cards into one image, and offers paid add-ons over Telegram
Stars. aiogram 3 (polling) + Anthropic SDK + Pillow + SQLite. See `README.md`.

## Build & test

```bash
pip install -r requirements-dev.txt
cp .env.example .env            # set BOT_TOKEN, ANTHROPIC_API_KEY
python main.py
pytest                          # pure-core tests only
ruff check . && black --check .
python tools/generate_cards.py  # regenerate the 78 card images
```

## Architecture invariant

"Clean core + thin layer", same as the sibling Telegram bots.

- **Core (aiogram/Pillow/network-free, unit-tested):** `bot/deck.py`,
  `bot/card_names.py`, `bot/daily.py` (`day_key`), `bot/db.py`, `bot/i18n.py`,
  `bot/pricing.py`, `bot/config.py`, and the `build_*` / `*_system_prompt`
  functions in `bot/interpret.py`. Keep new logic here.
- **Thin layer (not unit-tested):** `bot/handlers/`, `bot/service.py`,
  `bot/cards_render.py`, `bot/keyboards.py`, `main.py`, and the `Interpreter`
  class (the only thing in `interpret.py` that touches the network).

## Gotchas — do not regress

- **The daily reading is NOT fortune-telling.** The system prompt
  (`interpret.system_prompt`) explains the *current disposition* and forbids
  prediction. Only the paid `future` add-on uses `future_system_prompt`. Don't
  blur the two — it's the product's premise (`test_interpret.py` guards the
  prompt text).
- **A spread is fixed per (user, day).** `deck.draw(scope_key, 3)` is
  deterministic (seeded via SHA-256, independent of `PYTHONHASHSEED`), and
  `db.get_or_create_spread` uses `INSERT OR IGNORE` on a UNIQUE `scope_key`. The
  interpretation is generated once and cached in the row. Every `service.ensure_*`
  op is idempotent — a repeated request (or a retried payment) reuses stored
  cards and text instead of re-drawing or re-billing the model.
- **`deck.draw` uses a partial Fisher-Yates with the prefix property:** for the
  same key, the first *k* of a larger draw equals a smaller draw. That's why a
  `+2` and a `+5` clarification off the same parent share their first two cards
  (`extra_key = f"{scope_key}:extra:{count}"`). Don't swap it for `random.sample`
  — you'd lose the prefix property and the determinism guarantees.
- **Extra clarifying cards `exclude` the spread's own cards** so a clarification
  never repeats a card already on the table (`service.ensure_extra`).
- **Card identity is permanent.** A card `id` (`major_00`, `wands_01`,
  `cups_queen`, …) is persisted in the DB and is the asset filename
  (`assets/cards/<id>.png`). Never renumber or rename an existing card.
- **`day_key` is computed in the configured `TZ`** from `datetime.now(UTC)` then
  converted — this defines when the daily spread rolls over. Regression test in
  `test_daily.py` covers the timezone boundary.
- **Card art is swappable without code changes.** `cards_render` loads
  `assets/cards/<id>.png` and falls back to procedural rendering if absent; the
  bundled PNGs are procedural placeholders. Replace the PNGs (same filenames) to
  ship real Thoth-style art. The single-card renderer lives in
  `cards_render.render_card` and is also what `tools/generate_cards.py` writes.
- **Central card emblems are drawn as vector shapes, not font glyphs**
  (`cards_render._draw_symbol`) — geometric Unicode glyphs render as missing-box
  tofu in DejaVu, so triangle/diamond/square/star are drawn with `ImageDraw`.
- **DB calls are synchronous sqlite3 wrapped in `asyncio.to_thread`** by the
  thin layer (`service.py`, handlers). Keep `db.py` methods sync and testable;
  never `await` them directly — wrap at the call site so the event loop stays
  free.
- **The SQLite connection is opened `check_same_thread=False` and guarded by a
  `threading.Lock`** (`db.Database`). This is mandatory, not optional: because
  handlers reach the connection from `asyncio.to_thread` worker threads (not the
  thread that opened it), the default `check_same_thread=True` makes every DB
  call raise `sqlite3.ProgrammingError` and the bot silently stops replying. The
  lock serializes access across those threads. `test_usable_from_another_thread`
  guards this — a same-thread-only test suite will NOT catch a regression here.
- **Claude is called without extended thinking** (Opus 4.8 runs without thinking
  when `thinking` is omitted). The system prompt tells it to answer directly, no
  thinking aloud — because with thinking off Opus 4.8 can otherwise leak
  reasoning into the visible text. Keep that instruction if you change the call.
- **Telegram Stars invoices use `currency="XTR"` and an empty `provider_token`.**
  Product codes (`context_reading`, `future`, `extra_2`, `extra_5`) are embedded
  in the invoice payload and persisted in `purchases`, so keep them stable
  (`pricing.py`). Payloads are `"{product}:{spread_id}"`, or `"{product}:ctx"`
  for the context flow.
- **Up-sell model: each add-on is once per spread; buttons re-appear after
  every paid message.** `future`/`+2`/`+5` attach to a specific spread and are
  consumed once each (`service.purchased_addons` derives what's bought from
  `spreads.future_text` + `extra_draws`). `offers_keyboard(..., purchased)`
  hides bought add-ons; `render.send_offers` re-posts the keyboard after the
  daily spread AND after each paid add-on message. `cb_buy` refuses a stale
  button for an already-bought add-on (toast `already_bought`) so Stars aren't
  charged for a cached result. The **"reading for a situation"** button
  (`ctx`) is always shown — a context reading is a fresh, independent spread
  and is unlimited per day; each one gets its own once-each add-on set.
- **The context-reading situation rides in FSM state, not the invoice payload**
  (payloads are ≤128 bytes). `ContextFlow.waiting_situation` → the user's text is
  stored via `state.update_data(situation=...)` → invoice → on
  `successful_payment` the handler reads it back and clears state.
- **`i18n` requires matching key sets across ru/uk/en** (`test_i18n.py`), with
  lookup falling back ru→en→raw-key. Add a key to all three languages.
- **Callback/message handlers guard `from_user is None`** before using `.id`.
- **Router include order matters** (`handlers.all_routers`): `common` (owns the
  commands, incl. `/cancel`) is first, so the `ContextFlow.waiting_situation`
  text handler in `payments` only ever catches non-command text.
- **Dependencies are injected via the dispatcher** (`dp["db"]`, `dp["cfg"]`,
  `dp["interp"]`) and received by handlers as parameters named `db` / `cfg` /
  `interp`. Keep those names in sync.

## Out of scope (deliberate)

No fortune-telling in the free/context readings (only the paid `future` add-on
looks ahead), no reversed cards, one deck, no per-user timezone, no web
dashboard.

## License / credits

MIT. Card *data* (names, Thoth titles) is factual; bundled card art is original
procedural work — no third-party Thoth scans are included.
