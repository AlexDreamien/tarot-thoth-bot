"""Export one user's full reading history to a plain-text file.

Writes ``readings_<user_id>_<YYYY-MM-DD>.txt`` next to this script (override
with ``--out``). Each reading includes its date and time, type, the situation
(for situation readings), the card names, the interpretation, the future
reading, the expanded versions, and any clarifying draws.

    # list the users in the database
    python tools/export_readings.py --list

    # export one user
    python tools/export_readings.py 206998779

The production database lives on the Fly volume. Grab a copy first, then run
against it:

    flyctl ssh sftp get /data/tarot.db ./tarot.db --app tarot-thoth-bot
    python tools/export_readings.py 206998779 --db ./tarot.db

Times are stored in UTC and printed in --tz (default: the TZ env var, else
Europe/Kyiv).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.card_names import card_name  # noqa: E402
from bot.db import split_cards  # noqa: E402
from bot.deck import get_card  # noqa: E402

HERE = Path(__file__).resolve().parent
RULE = "=" * 72


def _connect(path: str) -> sqlite3.Connection:
    if not Path(path).exists():
        sys.exit(f"database not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _local(ts: str | None, tz: ZoneInfo) -> str:
    """Stored ISO-8601 UTC timestamp -> 'YYYY-MM-DD HH:MM:SS' in ``tz``."""
    if not ts:
        return "?"
    try:
        return datetime.fromisoformat(ts).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


def _cards(raw: str, lang: str) -> str:
    return " · ".join(card_name(get_card(c), lang) for c in split_cards(raw))


def _section(title: str, body: str | None) -> list[str]:
    return [f"--- {title} ---", body.strip(), ""] if body and body.strip() else []


def list_users(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""SELECT u.user_id, u.name, u.lang, u.created_at,
                  (SELECT COUNT(*) FROM spreads s WHERE s.user_id = u.user_id) AS n
           FROM users u ORDER BY n DESC, u.user_id""").fetchall()
    print(f"{'user_id':>12}  {'readings':>8}  {'lang':<4}  name")
    for r in rows:
        print(f"{r['user_id']:>12}  {r['n']:>8}  {r['lang']:<4}  {r['name'] or ''}")


def export(conn: sqlite3.Connection, user_id: int, tz: ZoneInfo, lang_override: str | None) -> str:
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if user is None:
        sys.exit(f"no such user: {user_id} (try --list)")
    lang = lang_override or user["lang"]

    spreads = conn.execute(
        "SELECT * FROM spreads WHERE user_id=? ORDER BY day, id", (user_id,)
    ).fetchall()

    out: list[str] = [
        RULE,
        f"Расклады пользователя: {user['name'] or '—'} (id {user_id})",
        f"Язык: {user['lang']}   Регистрация: {_local(user['created_at'], tz)}",
        f"Всего раскладов: {len(spreads)}   Время указано в {tz.key}",
        f"Выгружено: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}",
        RULE,
        "",
    ]

    for s in spreads:
        kind = "расклад под ситуацию" if s["kind"] == "context" else "ежедневный расклад"
        out += [
            RULE,
            f"{_local(s['created_at'], tz)}   {kind}   (день {s['day']})",
            RULE,
        ]
        if s["situation"]:
            out += [f"ЗАПРОС: {s['situation'].strip()}", ""]
        out += [f"КАРТЫ: {_cards(s['card_ids'], lang)}", ""]
        out += _section("ТОЛКОВАНИЕ", s["interpretation"])
        out += _section("РАЗВЁРНУТОЕ ТОЛКОВАНИЕ", s["long_text"])
        out += _section("ВЗГЛЯД В БУДУЩЕЕ", s["future_text"])
        out += _section("БУДУЩЕЕ — РАЗВЁРНУТО", s["future_long_text"])

        for e in conn.execute(
            "SELECT * FROM extra_draws WHERE spread_id=? ORDER BY count, id", (s["id"],)
        ):
            out += [
                f"--- +{e['count']} УТОЧНЯЮЩИХ КАРТ ({_local(e['created_at'], tz)}) ---",
                f"КАРТЫ: {_cards(e['card_ids'], lang)}",
                "",
            ]
            out += _section("ТОЛКОВАНИЕ", e["interpretation"])
            out += _section("РАЗВЁРНУТОЕ ТОЛКОВАНИЕ", e["long_text"])
        out.append("")

    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("user_id", nargs="?", type=int, help="Telegram user id to export")
    ap.add_argument(
        "--db", default=os.getenv("DB_PATH", "tarot.db"), help="path to the SQLite file"
    )
    ap.add_argument("--out", help="output file (default: next to this script)")
    ap.add_argument("--tz", default=os.getenv("TZ", "Europe/Kyiv"), help="time zone for timestamps")
    ap.add_argument("--lang", help="card-name language (ru/uk/en); default: the user's own")
    ap.add_argument("--list", action="store_true", help="list users and exit")
    args = ap.parse_args()

    conn = _connect(args.db)
    if args.list:
        list_users(conn)
        return
    if args.user_id is None:
        ap.error("user_id is required (or use --list)")

    tz = ZoneInfo(args.tz)
    text = export(conn, args.user_id, tz, args.lang)
    out = (
        Path(args.out)
        if args.out
        else HERE / f"readings_{args.user_id}_{datetime.now(tz):%Y-%m-%d}.txt"
    )
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out}  ({len(text):,} chars)")


if __name__ == "__main__":
    main()
