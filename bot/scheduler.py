"""Reminder scheduling (thin layer, not unit-tested — the decision logic it
calls lives in :func:`due_reminders`, which is pure and tested).

One APScheduler job ticks every 10 minutes and, for each user, works out their
*local* time from their stored UTC offset (falling back to the bot's configured
TZ). Users with ``reminder_hour`` set get a daily nudge at that local hour;
users who turned reminders off get a silent one once a week at 13:00 local.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config
from .db import Database
from .i18n import t
from .keyboards import newday_keyboard

log = logging.getLogger(__name__)

TICK_MINUTES = 10
WEEKLY_HOUR = 13  # local hour for the silent weekly nudge
WEEKLY_DAYS = 7
BIO_HINT_DAYS = 7  # how often a bio-less querent is invited to write one


def local_now(now_utc: datetime, offset_min: int | None, tz_name: str) -> datetime:
    """A user's local time: their stored UTC offset, or the bot's TZ if unset."""
    if offset_min is None:
        return now_utc.astimezone(ZoneInfo(tz_name))
    return now_utc.astimezone(UTC) + timedelta(minutes=offset_min)


def due_reminders(users, now_utc: datetime, tz_name: str) -> list[tuple[int, str, bool]]:
    """Pure decision core: who should be pinged right now.

    Returns ``(user_id, local_day, silent)`` tuples. A daily reminder fires in
    the tick window at the start of the user's chosen local hour, at most once
    per local day. Users with reminders off get a silent nudge at
    ``WEEKLY_HOUR`` local, at most once every ``WEEKLY_DAYS`` days.
    """
    out: list[tuple[int, str, bool]] = []
    for u in users:
        local = local_now(now_utc, u["tz_offset_min"], tz_name)
        day = local.strftime("%Y-%m-%d")
        in_window = local.minute < TICK_MINUTES
        hour = u["reminder_hour"]
        if hour is not None:
            if local.hour == hour and in_window and u["last_reminder_day"] != day:
                out.append((u["user_id"], day, False))
        elif local.hour == WEEKLY_HOUR and in_window:
            last = u["last_weekly_day"]
            if last is None or (local.date() - datetime.strptime(last, "%Y-%m-%d").date()).days >= (
                WEEKLY_DAYS
            ):
                out.append((u["user_id"], day, True))
    return out


def bio_hint_due(user, local_day: str) -> bool:
    """Pure: should this reminder also invite them to fill in "about you"?

    Only for a querent who hasn't written one, and at most once every
    ``BIO_HINT_DAYS`` local days — the reminder is a daily message and the
    invitation must not ride along with every single one. Takes the day as a
    day-key rather than reading a clock, like the rest of the decision core.
    """
    if (user["bio"] or "").strip():
        return False
    last = user["last_bio_hint_day"]
    if not last:
        return True
    return (date.fromisoformat(local_day) - date.fromisoformat(last)).days >= BIO_HINT_DAYS


class ReminderScheduler:
    def __init__(self, bot: Bot, db: Database, cfg: Config):
        self.bot = bot
        self.db = db
        self.cfg = cfg
        self.sched = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        # No next_run_time= here: passing None would add the job *paused* and
        # no reminder would ever fire.
        self.sched.add_job(self.tick, "interval", minutes=TICK_MINUTES)
        self.sched.start()
        log.info("Reminder scheduler started (tick every %d min)", TICK_MINUTES)

    async def shutdown(self) -> None:
        self.sched.shutdown(wait=False)

    async def tick(self) -> None:
        users = await asyncio.to_thread(self.db.all_users_for_scheduling)
        by_id = {u["user_id"]: u for u in users}
        now = datetime.now(UTC)
        for user_id, day, silent in due_reminders(users, now, self.cfg.tz):
            # Already drew today? Then the nudge is noise — but still record it
            # so we don't re-check every tick.
            drew = await asyncio.to_thread(self.db.has_daily_spread, user_id, day)
            if not drew:
                hint = bio_hint_due(by_id[user_id], day)
                await self._send(user_id, silent, hint)
                if hint:
                    await asyncio.to_thread(self.db.mark_bio_hint_sent, user_id, day)
            if silent:
                await asyncio.to_thread(self.db.mark_weekly_sent, user_id, day)
            else:
                await asyncio.to_thread(self.db.mark_reminder_sent, user_id, day)

    async def _send(self, user_id: int, silent: bool, bio_hint: bool = False) -> None:
        lang = await asyncio.to_thread(self.db.get_lang, user_id)
        lang = lang or self.cfg.default_lang
        key = "weekly_msg" if silent else "reminder_msg"
        text = t(lang, key)
        if bio_hint:
            text += "\n\n" + t(lang, "bio_hint")
        try:
            await self.bot.send_message(
                user_id,
                text,
                reply_markup=newday_keyboard(lang, bio_hint=bio_hint),
                disable_notification=silent,
            )
        except Exception as e:  # user blocked the bot, chat deleted, …
            log.info("reminder to %s failed: %s", user_id, e)
