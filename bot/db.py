"""SQLite persistence.

Pure core (no aiogram/network), unit-tested against a temp database. Methods
are synchronous sqlite3 calls; the thin async layer wraps them in
``asyncio.to_thread`` so the event loop is never blocked.

Idempotency is the point: a spread is keyed by a deterministic ``scope_key``
(``INSERT OR IGNORE``), so a retried request reuses the same cards and the same
stored interpretation instead of drawing or charging twice.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime

DEFAULT_REMINDER_HOUR = 9  # 09:00 local, unless the user changes it


def _now() -> str:
    return datetime.now(UTC).isoformat()


def join_cards(card_ids: list[str]) -> str:
    return ",".join(card_ids)


def split_cards(raw: str) -> list[str]:
    return [c for c in raw.split(",") if c]


class Database:
    def __init__(self, path: str):
        # check_same_thread=False: the async layer calls these methods from
        # asyncio.to_thread worker threads, not the thread that opened the
        # connection. A single Lock serializes all access so the shared
        # connection is used safely across those threads.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.Lock()
        self._migrate()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def _migrate(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                lang       TEXT NOT NULL,
                name       TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS spreads (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                day            TEXT NOT NULL,
                kind           TEXT NOT NULL,
                scope_key      TEXT NOT NULL UNIQUE,
                situation      TEXT,
                card_ids       TEXT NOT NULL,
                interpretation TEXT,
                future_text    TEXT,
                created_at     TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_spreads_user ON spreads(user_id, id);

            CREATE TABLE IF NOT EXISTS extra_draws (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                spread_id      INTEGER NOT NULL REFERENCES spreads(id),
                count          INTEGER NOT NULL,
                card_ids       TEXT NOT NULL,
                interpretation TEXT,
                created_at     TEXT NOT NULL,
                UNIQUE(spread_id, count)
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                product    TEXT NOT NULL,
                stars      INTEGER NOT NULL,
                charge_id  TEXT,
                created_at TEXT NOT NULL
            );
            """)
        self._add_column("users", "name", "TEXT")
        # Reminder settings. reminder_hour NULL == reminders off (those users
        # get the weekly silent nudge instead); tz_offset_min NULL == use the
        # bot's configured TZ.
        if self._add_column("users", "reminder_hour", "INTEGER"):
            self.conn.execute("UPDATE users SET reminder_hour=?", (DEFAULT_REMINDER_HOUR,))
        self._add_column("users", "tz_offset_min", "INTEGER")
        self._add_column("users", "last_reminder_day", "TEXT")
        self._add_column("users", "last_weekly_day", "TEXT")
        # Expanded ("tell me more") interpretations, generated on demand.
        self._add_column("spreads", "long_text", "TEXT")
        self._add_column("spreads", "future_long_text", "TEXT")
        self._add_column("extra_draws", "long_text", "TEXT")
        self.conn.commit()

    def _add_column(self, table: str, col: str, decl: str) -> bool:
        """Add a column to an existing table if it's missing (forward migration
        for databases created before the column existed). Returns True if the
        column was actually added."""
        existing = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
        if col in existing:
            return False
        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        return True

    # --- users -----------------------------------------------------------

    def get_or_create_user(self, user_id: int, default_lang: str, name: str | None = None) -> str:
        with self._lock:
            row = self.conn.execute(
                "SELECT lang, name FROM users WHERE user_id=?", (user_id,)
            ).fetchone()
            if row:
                if name and name != row["name"]:
                    self.conn.execute("UPDATE users SET name=? WHERE user_id=?", (name, user_id))
                    self.conn.commit()
                return row["lang"]
            self.conn.execute(
                """INSERT INTO users(user_id, lang, name, reminder_hour, created_at)
                   VALUES(?,?,?,?,?)""",
                (user_id, default_lang, name, DEFAULT_REMINDER_HOUR, _now()),
            )
            self.conn.commit()
            return default_lang

    def get_lang(self, user_id: int) -> str | None:
        with self._lock:
            row = self.conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
            return row["lang"] if row else None

    def set_lang(self, user_id: int, lang: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
            self.conn.commit()

    # --- reminder settings / scheduling ----------------------------------

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

    def set_reminder_hour(self, user_id: int, hour: int | None) -> None:
        """``hour`` 0..23, or None to switch daily reminders off."""
        with self._lock:
            self.conn.execute("UPDATE users SET reminder_hour=? WHERE user_id=?", (hour, user_id))
            self.conn.commit()

    def set_tz_offset(self, user_id: int, minutes: int | None) -> None:
        """UTC offset in minutes, or None to follow the bot's configured TZ."""
        with self._lock:
            self.conn.execute(
                "UPDATE users SET tz_offset_min=? WHERE user_id=?", (minutes, user_id)
            )
            self.conn.commit()

    def all_users_for_scheduling(self) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute("""SELECT user_id, lang, reminder_hour, tz_offset_min,
                          last_reminder_day, last_weekly_day
                   FROM users""").fetchall()

    def mark_reminder_sent(self, user_id: int, day: str) -> None:
        with self._lock:
            self.conn.execute(
                "UPDATE users SET last_reminder_day=? WHERE user_id=?", (day, user_id)
            )
            self.conn.commit()

    def mark_weekly_sent(self, user_id: int, day: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE users SET last_weekly_day=? WHERE user_id=?", (day, user_id))
            self.conn.commit()

    def has_daily_spread(self, user_id: int, day: str) -> bool:
        with self._lock:
            row = self.conn.execute(
                "SELECT 1 FROM spreads WHERE user_id=? AND day=? AND kind='daily' LIMIT 1",
                (user_id, day),
            ).fetchone()
        return row is not None

    # --- spreads ---------------------------------------------------------

    def get_or_create_spread(
        self,
        *,
        user_id: int,
        day: str,
        kind: str,
        scope_key: str,
        card_ids: list[str],
        situation: str | None = None,
    ) -> sqlite3.Row:
        """Return the spread for ``scope_key``, creating it if absent.

        Concurrent-safe via the UNIQUE(scope_key) constraint and INSERT OR
        IGNORE: two racing requests can't create two spreads for the same key.
        """
        with self._lock:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO spreads
                    (user_id, day, kind, scope_key, situation, card_ids, created_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (user_id, day, kind, scope_key, situation, join_cards(card_ids), _now()),
            )
            self.conn.commit()
            return self.conn.execute(
                "SELECT * FROM spreads WHERE scope_key=?", (scope_key,)
            ).fetchone()

    def get_spread(self, spread_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute("SELECT * FROM spreads WHERE id=?", (spread_id,)).fetchone()

    def get_last_spread(self, user_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM spreads WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()

    def set_interpretation(self, spread_id: int, text: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE spreads SET interpretation=? WHERE id=?", (text, spread_id))
            self.conn.commit()

    def set_spread_long(self, spread_id: int, text: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE spreads SET long_text=? WHERE id=?", (text, spread_id))
            self.conn.commit()

    def set_future_long(self, spread_id: int, text: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE spreads SET future_long_text=? WHERE id=?", (text, spread_id))
            self.conn.commit()

    def set_extra_long(self, extra_id: int, text: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE extra_draws SET long_text=? WHERE id=?", (text, extra_id))
            self.conn.commit()

    def get_extra(self, extra_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute("SELECT * FROM extra_draws WHERE id=?", (extra_id,)).fetchone()

    def set_future(self, spread_id: int, text: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE spreads SET future_text=? WHERE id=?", (text, spread_id))
            self.conn.commit()

    # --- extra draws -----------------------------------------------------

    def get_or_create_extra(
        self, *, spread_id: int, count: int, card_ids: list[str]
    ) -> sqlite3.Row:
        with self._lock:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO extra_draws (spread_id, count, card_ids, created_at)
                VALUES (?,?,?,?)
                """,
                (spread_id, count, join_cards(card_ids), _now()),
            )
            self.conn.commit()
            return self.conn.execute(
                "SELECT * FROM extra_draws WHERE spread_id=? AND count=?",
                (spread_id, count),
            ).fetchone()

    def set_extra_interpretation(self, extra_id: int, text: str) -> None:
        with self._lock:
            self.conn.execute(
                "UPDATE extra_draws SET interpretation=? WHERE id=?", (text, extra_id)
            )
            self.conn.commit()

    def extra_counts(self, spread_id: int) -> set[int]:
        """The ``count`` of every extra draw already bought for this spread
        (used to hide add-ons that are consumed once per spread)."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT count FROM extra_draws WHERE spread_id=?", (spread_id,)
            ).fetchall()
            return {r["count"] for r in rows}

    def all_extra_cards(self, spread_id: int) -> list[str]:
        """Every card id already drawn as a clarifying card for this spread, so
        a follow-up draw (e.g. +3 after +2) never repeats one."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT card_ids FROM extra_draws WHERE spread_id=?", (spread_id,)
            ).fetchall()
        out: list[str] = []
        for r in rows:
            out.extend(split_cards(r["card_ids"]))
        return out

    # --- history (a user's own past readings) ----------------------------

    def reading_day_keys(self, user_id: int) -> set[str]:
        """Distinct ``YYYY-MM-DD`` dates on which this user has any spread."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT DISTINCT day FROM spreads WHERE user_id=?", (user_id,)
            ).fetchall()
        return {r["day"] for r in rows}

    def spreads_on_day(self, user_id: int, day: str) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM spreads WHERE user_id=? AND day=? ORDER BY id", (user_id, day)
            ).fetchall()

    def get_owned_spread(self, user_id: int, spread_id: int) -> sqlite3.Row | None:
        """A spread by id, but only if it belongs to ``user_id`` (access guard)."""
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM spreads WHERE id=? AND user_id=?", (spread_id, user_id)
            ).fetchone()

    def recent_readings(
        self, user_id: int, limit: int, exclude_id: int | None = None
    ) -> list[sqlite3.Row]:
        """This user's last ``limit`` finished readings, newest first — the raw
        material for ``memory.render_block``.

        Only readings that actually got an interpretation count as history (a
        row that was drawn but never read is not something the querent saw), and
        ``exclude_id`` drops the spread being read right now, which is already
        in the table by the time we build its prompt. Clarifying cards come
        along in ``extra_card_ids``: they were on the table too.

        User-scoped in SQL, like every other archive query — one querent's
        history must never reach another's reading.
        """
        sql = """SELECT s.id, s.day, s.kind, s.situation, s.card_ids,
                        (SELECT group_concat(e.card_ids, ',') FROM extra_draws e
                          WHERE e.spread_id = s.id) AS extra_card_ids
                   FROM spreads s
                  WHERE s.user_id = ? AND s.interpretation IS NOT NULL"""
        params: list[object] = [user_id]
        if exclude_id is not None:
            sql += " AND s.id <> ?"
            params.append(exclude_id)
        params.append(limit)
        with self._lock:
            return self.conn.execute(sql + " ORDER BY s.id DESC LIMIT ?", params).fetchall()

    def extras_for_spread(self, spread_id: int) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM extra_draws WHERE spread_id=? ORDER BY count", (spread_id,)
            ).fetchall()

    # --- purchases -------------------------------------------------------

    def log_purchase(
        self, *, user_id: int, product: str, stars: int, charge_id: str | None
    ) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO purchases(user_id, product, stars, charge_id, created_at)
                VALUES (?,?,?,?,?)
                """,
                (user_id, product, stars, charge_id, _now()),
            )
            self.conn.commit()

    def stats(self) -> dict[str, int]:
        with self._lock:
            c = self.conn
            users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            spreads = c.execute("SELECT COUNT(*) FROM spreads").fetchone()[0]
            purchases = c.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
            stars = c.execute("SELECT COALESCE(SUM(stars),0) FROM purchases").fetchone()[0]
            return {
                "users": users,
                "spreads": spreads,
                "purchases": purchases,
                "stars": stars,
            }
