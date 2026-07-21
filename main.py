"""Entry point: wires config, DB, the Claude interpreter and the routers, then
runs long polling. Thin — all logic lives in ``bot/``."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import load_config
from bot.db import Database
from bot.handlers import all_routers
from bot.interpret import Interpreter

_COMMANDS = [
    BotCommand(command="tarot", description="Расклад на сегодня / Today's spread"),
    BotCommand(command="help", description="Как это работает / How it works"),
    BotCommand(command="lang", description="Язык / Language"),
]


async def _set_commands(bot: Bot) -> None:
    await bot.set_my_commands(_COMMANDS)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    cfg = load_config()
    if not cfg.anthropic_key_present:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — the bot needs it to generate readings.")

    db = Database(cfg.db_path)
    interp = Interpreter(cfg.claude_model)

    bot = Bot(cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["cfg"] = cfg
    dp["interp"] = interp
    for router in all_routers():
        dp.include_router(router)

    await _set_commands(bot)
    logging.info("Tarot Thoth bot started (model=%s, tz=%s)", cfg.claude_model, cfg.tz)
    try:
        await dp.start_polling(bot)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
