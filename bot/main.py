"""Точка входа: настройка диспетчера, мидлвэров и запуск polling."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.db import init_db
from bot.handlers import build_router
from bot.middlewares import DbSessionMiddleware, UserUpsertMiddleware


async def _on_startup(bot: Bot) -> None:
    me = await bot.get_me()
    logging.info("Bot started: @%s (id=%s)", me.username, me.id)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not settings.bot_token or settings.bot_token.startswith("123456:"):
        logging.error("BOT_TOKEN не задан. Проверьте .env (см. .env.example).")
        sys.exit(1)
    if not settings.owner_id:
        logging.warning("OWNER_ID не задан — у бота не будет владельца.")

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # порядок мидлвэров: сначала сессия, затем апсерт юзера (использует сессию)
    db_mw = DbSessionMiddleware()
    user_mw = UserUpsertMiddleware()
    dp.message.middleware(db_mw)
    dp.message.middleware(user_mw)
    dp.callback_query.middleware(db_mw)
    dp.callback_query.middleware(user_mw)

    dp.include_router(build_router())
    dp.startup.register(_on_startup)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
