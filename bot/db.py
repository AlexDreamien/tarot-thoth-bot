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
        self.conn.commit()

    # --- users -----------------------------------------------------------

    def get_or_create_user(self, user_id: int, default_lang: str) -> str:
        with self._lock:
            row = self.conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
            if row:
                return row["lang"]
            self.conn.execute(
                "INSERT INTO users(user_id, lang, created_at) VALUES(?,?,?)",
                (user_id, default_lang, _now()),
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
