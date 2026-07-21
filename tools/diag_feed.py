"""One-off diagnostic: exercise the real reply path inside the deployed
container. Does get_me, a direct send to the admin, and drives a /start update
through the actual dispatcher (routers + dependency injection). Surfaces exactly
where a reply breaks. Piped in over SSH (`cd /app && python -`); not part of the
image or the test suite.
"""

from __future__ import annotations

import asyncio
import datetime
import traceback

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

from bot.config import load_config
from bot.db import Database
from bot.handlers import all_routers
from bot.interpret import Interpreter

UID = 273688933


async def main() -> None:
    cfg = load_config()
    bot = Bot(cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    try:
        me = await bot.get_me()
        print("GETME:", me.username)
    except Exception:
        print("GETME_ERROR:")
        traceback.print_exc()

    try:
        await bot.send_message(UID, "diag: direct ping from the bot")
        print("SEND_OK")
    except Exception:
        print("SEND_ERROR:")
        traceback.print_exc()

    db = Database(cfg.db_path)
    interp = Interpreter(cfg.claude_model)
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["cfg"] = cfg
    dp["interp"] = interp
    for router in all_routers():
        dp.include_router(router)

    message = Message(
        message_id=999999,
        date=datetime.datetime.now(datetime.UTC),
        chat=Chat(id=UID, type="private"),
        from_user=User(id=UID, is_bot=False, first_name="Diag"),
        text="/start",
    ).as_(bot)
    update = Update(update_id=1, message=message)

    try:
        res = await dp.feed_update(bot, update)
        print("FEED_OK result=", res)
    except Exception:
        print("FEED_ERROR:")
        traceback.print_exc()

    await bot.session.close()


asyncio.run(main())
