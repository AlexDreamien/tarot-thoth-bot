"""Export one user's full reading history to a plain-text file.

By default the script first downloads a fresh copy of the production database
from the Fly volume (``flyctl ssh sftp get``) into ``tools/tarot.db``, then
exports from it. Writes ``readings_<user_id>_<YYYY-MM-DD>.txt`` next to this
script (override with ``--out``). Each reading includes its date and time,
type, the situation (for situation readings), the card names, the
interpretation, the future reading, the expanded versions, and any clarifying
draws.

    # list the users (downloads a fresh DB first)
    python tools/export_readings.py --list

    # export one user
    python tools/export_readings.py 206998779

    # only readings in a date range (inclusive, by reading day)
    python tools/export_readings.py 206998779 --from 2026-08-01 --to 2026-08-04

    # reuse the copy already downloaded, or point at another file
    python tools/export_readings.py 206998779 --no-fetch
    python tools/export_readings.py 206998779 --db ./some-backup.db

Times are stored in UTC and printed in --tz (default: the TZ env var, else
Europe/Kyiv).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.card_names import card_name  # noqa: E402
from bot.db import split_cards  # noqa: E402
from bot.deck import get_card  # noqa: E402

HERE = Path(__file__).resolve().parent
RULE = "=" * 72

DEFAULT_APP = "tarot-thoth-bot"
REMOTE_DB = "/data/tarot.db"
LOCAL_DB = HERE / "tarot.db"  # gitignored (*.db)
SIDECARS = ("-wal", "-shm")  # SQLite's WAL companions, named "<db>-wal"


def _rm(path: Path) -> None:
    if path.exists():
        path.unlink()


def _sftp_get(flyctl: str, app: str, remote: str, dest: Path) -> tuple[bool, str]:
    """Download one file. ``fly ssh sftp get`` writes relative to the working
    directory, so we run it in the destination folder."""
    res = subprocess.run(
        [flyctl, "ssh", "sftp", "get", remote, dest.name, "--app", app],
        cwd=dest.parent,
        capture_output=True,
        text=True,
    )
    ok = res.returncode == 0 and dest.exists() and dest.stat().st_size > 0
    return ok, (res.stderr or res.stdout or f"exit code {res.returncode}").strip()


def _fold_wal(db_path: Path) -> None:
    """Replay the write-ahead log into the main file so the copy stands alone.
    Switching the journal mode checkpoints the WAL and removes the sidecars."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()


def _freshness(db_path: Path) -> str:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        n, newest = conn.execute("SELECT COUNT(*), MAX(day) FROM spreads").fetchone()
    return f"{n} readings, newest {newest or 'none'}"


def fetch_db(app: str, dest: Path) -> None:
    """Download the live database from the Fly volume next to this script.

    Two traps here, both hit in production:

    * ``fly ssh sftp get`` **refuses to overwrite** an existing file ("doesn't
      override existing files for safety"). Downloading straight onto the
      previous copy therefore fails every run after the first — and an earlier
      version of this function treated "the file is there and non-empty" as
      success, so it silently exported a stale snapshot while printing "Saved".
      Hence: fresh temp name, check the exit code, replace only on success.
    * The bot runs SQLite in **WAL mode**, so readings committed since the last
      checkpoint live in ``tarot.db-wal``, not in ``tarot.db``. The sidecars
      come along and are folded in locally; without that, today's readings can
      be missing from an otherwise perfectly fresh download.

    The previous copy is left untouched unless the new one arrives intact.
    """
    flyctl = shutil.which("flyctl") or shutil.which("fly")
    if not flyctl:
        sys.exit("flyctl not found — install it, or pass --no-fetch/--db to use a local copy")
    print(f"Downloading {REMOTE_DB} from {app} ...")

    staged = dest.with_name(dest.name + ".download")
    for suffix in ("", *SIDECARS):
        _rm(staged.with_name(staged.name + suffix))

    ok, err = _sftp_get(flyctl, app, REMOTE_DB, staged)
    if not ok:
        _rm(staged)
        sys.exit(f"download failed:\n{err}")
    # Best-effort: the sidecars exist only when the bot hasn't checkpointed yet.
    for suffix in SIDECARS:
        _sftp_get(flyctl, app, REMOTE_DB + suffix, staged.with_name(staged.name + suffix))

    _fold_wal(staged)
    for suffix in SIDECARS:
        _rm(staged.with_name(staged.name + suffix))
        _rm(dest.with_name(dest.name + suffix))
    staged.replace(dest)
    print(f"Saved {dest} ({dest.stat().st_size:,} bytes) - {_freshness(dest)}")


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


GENDER_LABEL = {"m": "м", "f": "ж"}


def _clip(text: object, width: int) -> str:
    """One line, at most ``width`` characters, em-dash for nothing."""
    if not text:
        return "—"
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def list_users(conn: sqlite3.Connection) -> None:
    """Who is in the database, with the preferences they've set.

    The persona columns arrived over several deploys, so an older copy of the
    database (``--db`` at a backup, or ``--no-fetch`` on a stale file) is still
    listed rather than crashing on a missing column.
    """
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}

    def col(name: str) -> str:
        return f"u.{name}" if name in have else "NULL"

    rows = conn.execute(f"""
        SELECT u.user_id, u.name, u.lang,
               {col("display_name")} AS display_name,
               {col("gender")} AS gender,
               {col("bio")} AS bio,
               (SELECT COUNT(*) FROM spreads s WHERE s.user_id = u.user_id) AS n,
               (SELECT MAX(day) FROM spreads s WHERE s.user_id = u.user_id) AS last_day
          FROM users u ORDER BY n DESC, u.user_id
    """).fetchall()

    head = (
        f"{'user_id':>12}  {'раскл':>5}  {'последний':<10}  {'яз':<3}  {'пол':<3}  "
        f"{'обращение':<14}  {'имя в Telegram':<18}  о себе"
    )
    print(head)
    print("-" * len(head))
    for r in rows:
        print(
            f"{r['user_id']:>12}  {r['n']:>5}  {r['last_day'] or '—':<10}  {r['lang']:<3}  "
            f"{GENDER_LABEL.get(r['gender'], '—'):<3}  {_clip(r['display_name'], 14):<14}  "
            f"{_clip(r['name'], 18):<18}  {_clip(r['bio'], 46)}"
        )


def export(
    conn: sqlite3.Connection,
    user_id: int,
    tz: ZoneInfo,
    lang_override: str | None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if user is None:
        sys.exit(f"no such user: {user_id} (try --list)")
    lang = lang_override or user["lang"]

    # spreads.day is 'YYYY-MM-DD', so a lexicographic range is a date range.
    sql = "SELECT * FROM spreads WHERE user_id=?"
    params: list[object] = [user_id]
    if date_from:
        sql += " AND day >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND day <= ?"
        params.append(date_to)
    spreads = conn.execute(sql + " ORDER BY day, id", params).fetchall()

    if date_from or date_to:
        period = f"Период: {date_from or '…'} — {date_to or '…'}"
    else:
        period = "Период: весь"
    out: list[str] = [
        RULE,
        f"Расклады пользователя: {user['name'] or '—'} (id {user_id})",
        f"Язык: {user['lang']}   Регистрация: {_local(user['created_at'], tz)}",
        f"{period}   Раскладов в выгрузке: {len(spreads)}",
        f"Время указано в {tz.key}",
        f"Выгружено: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}",
        RULE,
        "",
    ]
    if not spreads:
        out.append("(за указанный период раскладов нет)")

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
    ap.add_argument("--db", help="use this SQLite file instead of downloading from Fly")
    ap.add_argument("--no-fetch", action="store_true", help="reuse the already downloaded copy")
    ap.add_argument("--app", default=DEFAULT_APP, help="Fly app to download the database from")
    ap.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD", help="earliest reading day")
    ap.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD", help="latest reading day")
    ap.add_argument("--out", help="output file (default: next to this script)")
    ap.add_argument("--tz", default=os.getenv("TZ", "Europe/Kyiv"), help="time zone for timestamps")
    ap.add_argument("--lang", help="card-name language (ru/uk/en); default: the user's own")
    ap.add_argument("--list", action="store_true", help="list users and exit")
    args = ap.parse_args()

    for value in (args.date_from, args.date_to):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                ap.error(f"dates must be YYYY-MM-DD, got {value!r}")
    if args.date_from and args.date_to and args.date_from > args.date_to:
        ap.error("--from is later than --to")

    # An explicit --db (or --no-fetch) uses a local file; otherwise refresh.
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = LOCAL_DB
        if not args.no_fetch:
            fetch_db(args.app, db_path)

    conn = _connect(str(db_path))
    if args.list:
        list_users(conn)
        return
    if args.user_id is None:
        ap.error("user_id is required (or use --list)")

    tz = ZoneInfo(args.tz)
    text = export(conn, args.user_id, tz, args.lang, args.date_from, args.date_to)
    if args.out:
        out = Path(args.out)
    else:
        span = ""
        if args.date_from or args.date_to:
            span = f"_{args.date_from or 'start'}_{args.date_to or 'now'}"
        out = HERE / f"readings_{args.user_id}{span or f'_{datetime.now(tz):%Y-%m-%d}'}.txt"
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out}  ({len(text):,} chars)")


if __name__ == "__main__":
    main()
