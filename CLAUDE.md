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
  `bot/memory.py`, `bot/pricing.py`, `bot/config.py`, and the `build_*` /
  `*_system_prompt` functions in `bot/interpret.py`. Keep new logic here.
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
  `assets/cards/<id>.png` and falls back to `render_card` if absent. The bundled
  PNGs are an **original procedurally-drawn vector deck** (single-card renderer
  `cards_render.render_card`, also what `tools/generate_cards.py` writes).
  Replace the PNGs (same filenames) to ship different art.
- **All card emblems are drawn as vector shapes, never font glyphs** — geometric
  Unicode renders as missing-box tofu in DejaVu, so suit symbols, pip layouts,
  court medallions and the 22 Major emblems are composed from `ImageDraw`
  primitives. `render_card` supersamples 3× then downscales (LANCZOS) for smooth
  edges; `ImageDraw.arc` bounding boxes must be left→right / top→bottom (a
  reversed box raises `ValueError`).
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
- **Add-ons are gated by `cfg.payments_enabled` (env `PAYMENTS_ENABLED`,
  default off).** Off → tapping a button delivers the add-on **for free**
  immediately (`payments._deliver_addon` / `_deliver_context`); on → it's sold
  for Telegram Stars. Both paths share the same delivery helpers and the same
  once-per-spread rules. Keep the paid path working behind the flag — don't
  delete it. Button labels come from `offers_keyboard(..., paid)`: icon + text,
  with a `— ⭐N` (`price_suffix`) appended only when `paid`.
- **Telegram Stars invoices (paid mode) use `currency="XTR"` and an empty
  `provider_token`.** Product codes (`context_reading`, `future`, `extra_2`,
  `extra_3`, `extra_5`) are embedded in the invoice payload and persisted in
  `purchases`, so keep them stable (`pricing.py`). Payloads are
  `"{product}:{spread_id}"`, or `"{product}:ctx"` for the context flow.
- **Up-sell model: per-spread add-ons; buttons re-appear after every paid
  message showing only what's still valid.** `future` is once per spread.
  Clarifying cards are a **tiered upgrade toward five total**: with none bought,
  offer +2 (2⭐) or +5 (5⭐); after a +2, offer only a +3 top-up (3⭐, reaching
  five — 2+3 == 5⭐); at five (a +5, or +2 then +3) offer nothing more. The
  state machine is `service.spread_addon_state` (`(future_bought, "none"|"two"|
  "full")`) → `service.available_addons` → the ordered product list rendered by
  `offers_keyboard(lang, spread_id, available)`. **Every delivery path ends with
  `render.send_offers`** — daily/context spread, each add-on message, and the
  expanded reading (`_deliver_expand`, which resolves an `extra_id` back to its
  parent `spread_id` first and re-offers everything *except* expanding the same
  reading again). A path that forgets it dead-ends the chat: no add-ons, no
  new-day, no situation reading, since the keyboard is the only navigation the
  bot has. `test_expand_delivery.py` guards this. `cb_buy` refuses any product **not** in `available_for_spread` (toast
  `already_bought`) — this blocks both a re-buy and a stale +5 button after a
  +2. `ensure_extra` excludes `db.all_extra_cards` (base + prior clarifying
  cards) so a +3 never repeats the +2 cards. The **`ctx`** button is always
  shown — a context reading is a fresh, independent spread, unlimited per day,
  with its own tiered add-on set.
- **The context-reading situation rides in FSM state, not the invoice payload**
  (payloads are ≤128 bytes). `ContextFlow.waiting_situation` → the user's text is
  stored via `state.update_data(situation=...)` → invoice → on
  `successful_payment` the handler reads it back and clears state.
- **Readings are BRIEF by default; "expand" is a separate, cached generation.**
  `interpret.system_prompt(lang)` appends `_BRIEF` (3–5 sentences); the expand
  path uses `system_prompt(lang, deep=True)` + `Interpreter.expand(...)`, which
  is fed the original `build_*_user` block plus the short text so it deepens
  rather than repeats. Each target caches separately: `spreads.long_text`,
  `spreads.future_long_text`, `extra_draws.long_text`. Callbacks are
  `exp:s:<spread_id>` / `exp:f:<spread_id>` / `exp:e:<extra_id>` — every message
  carrying a reading passes its own `expand_cb` to `send_offers`.
- **`newday` button is on every action keyboard.** If the user already has a
  daily spread for `day_key(cfg.tz)` (`db.has_daily_spread`) it answers with
  `newday_already` and drops into the situation flow; otherwise it delivers the
  free daily spread via `handlers.spread.deliver_daily` (shared with `/tarot`).
- **Reminders: `scheduler.due_reminders` is the pure, tested decision core**; the
  APScheduler tick (every `TICK_MINUTES`) only does IO. Telegram never exposes a
  user's time zone — the user picks a UTC offset in `/settings`
  (`users.tz_offset_min`, NULL = the bot's `TZ`), and `users.reminder_hour` NULL
  means reminders are **off**, which switches them to one *silent*
  (`disable_notification=True`) nudge a week at `WEEKLY_HOUR` local. Guard rails:
  `last_reminder_day` / `last_weekly_day` make it at most once per local day/week,
  and a user who already drew today gets no ping. Never pass `next_run_time=None`
  to `add_job` — that adds the job **paused** and nothing ever fires.
- **The reading is given the querent's own past readings (`bot/memory.py`).**
  `db.recent_readings(user_id, MAX_SCANNED, exclude_id)` → `memory.from_rows` →
  `memory.render_block(...)` → the block rides in `build_daily_user` /
  `build_context_user`, and `system_prompt(..., memory=True)` appends
  `_MEMORY_RULE`. Invariants worth keeping: the block is **empty for a
  first-time querent** (an empty preamble invites the model to gesture at a past
  that isn't there) and the rule then isn't appended at all, so those prompts stay
  byte-identical to the pre-memory ones; `render_block` takes **`today` as a
  day-key, never a clock**, which is what makes it testable; only readings with
  an `interpretation` count as history and the spread being read right now is
  excluded by id (it's already in the table by prompt-building time); clarifying
  cards are folded into the reading they belong to. `MAX_SCANNED` (40) bounds
  the repeat search, `MAX_RECENT` (6) how many are actually named — ~300 tokens.
  Memory feeds the two readings that **open** a spread (daily, context) and their
  expansions; `future`/`extra` inherit it through the base interpretation they're
  given. Deliberately **cards and questions only, never past interpretation
  text**. Same privacy rule as `/history`: `recent_readings` is user-scoped in
  SQL — one querent's history must never reach another's prompt
  (`test_memory.py` guards this).
- **`render.thinking()` wraps ONLY the generation call.** It posts the
  "composing your reading…" placeholder *and* starts a task that re-sends the
  `typing` chat action every `TYPING_REFRESH` (4s) — Telegram drops the
  indicator after ~5s, and a reading takes 20s–2min, so a single action would
  leave the chat looking dead. Both are torn down in `finally`, so the result
  must be sent *after* the block. Chat actions go through `render.send_action`,
  which swallows everything: the indicator is decoration and must never take a
  delivery down (nor break on the tests' bot-less fake messages).
  `send_cards_photo` sets `upload_photo` for the compositing/upload beat that
  follows the block. Guarded in `test_split_text.py`.
- **`/history` is a per-user archive; every query is user-scoped in SQL.**
  `handlers/history.py` shows a month calendar (`keyboards.calendar_keyboard`,
  callbacks `hist:nav:YYYY-MM` / `hist:day:YYYY-MM-DD` / `hist:show:<id>` /
  `hist:noop`) of the user's own reading dates (`db.reading_day_keys`), and
  replays a stored reading in full (cards, interpretation, future, extras).
  Access control is the SQL `WHERE user_id=?` in `spreads_on_day` /
  `get_owned_spread` — never fetch a spread for replay via unscoped
  `get_spread`. Dates are the `spreads.day` day-key (`YYYY-MM-DD`, sortable).
- **Schema changes to existing tables use `db._add_column` (forward migration).**
  The prod SQLite lives on a Fly volume and predates newer columns (e.g.
  `users.name`); `CREATE TABLE IF NOT EXISTS` won't add a column, so `_migrate`
  calls `_add_column("users", "name", "TEXT")` which `ALTER TABLE ADD COLUMN`s
  only if `PRAGMA table_info` shows it missing. Use this for any new column on
  an existing table — never assume a fresh DB.
- **Calendar month/weekday labels are `i18n.MONTHS`/`WEEKDAYS`, not `_STRINGS`**
  (they're lists, and the `test_i18n` key-matching test only covers `_STRINGS`).
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
