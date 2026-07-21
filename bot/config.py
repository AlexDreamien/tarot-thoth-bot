"""Runtime configuration loaded from the environment (.env).

Pure core: reads env once into a frozen dataclass, no side effects beyond that.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from .i18n import DEFAULT_LANG as _FALLBACK_LANG
from .i18n import LANGS


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    claude_model: str
    tz: str
    db_path: str
    default_lang: str
    anthropic_key_present: bool = field(default=False)


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return frozenset(ids)


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set — copy .env.example to .env and fill it in")

    default_lang = os.getenv("DEFAULT_LANG", _FALLBACK_LANG).strip().lower()
    if default_lang not in LANGS:
        default_lang = _FALLBACK_LANG

    return Config(
        bot_token=token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-opus-4-8").strip(),
        tz=os.getenv("TZ", "Europe/Kyiv").strip(),
        db_path=os.getenv("DB_PATH", "tarot.db").strip(),
        default_lang=default_lang,
        anthropic_key_present=bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
    )
