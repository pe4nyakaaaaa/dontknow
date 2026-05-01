"""FastAPI app entrypoint for the Mini App backend.

Также запускает aiogram polling в фоновой задаче, чтобы бот и API жили в одном
процессе и работали с одной БД (на Fly это /data/app.db). Если нужно запускать
бота отдельным процессом, задайте `RUN_BOT=0`.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    admin,
    cart,
    catalog,
    courier,
    disputes,
    me,
    orders,
    reviews,
    wallet,
)
from bot.config import settings
from bot.db import init_db
from bot.handlers import build_router
from bot.middlewares import DbSessionMiddleware, UserUpsertMiddleware


async def _start_bot_polling() -> None:
    """Запуск aiogram polling. Конфигурация дублирует bot/main.py:_main."""
    if not settings.bot_token or settings.bot_token.startswith("123456:"):
        logging.warning("BOT_TOKEN не задан — бот не запущен.")
        return
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    db_mw = DbSessionMiddleware()
    user_mw = UserUpsertMiddleware()
    dp.message.middleware(db_mw)
    dp.message.middleware(user_mw)
    dp.callback_query.middleware(db_mw)
    dp.callback_query.middleware(user_mw)
    dp.include_router(build_router())

    try:
        me_info = await bot.get_me()
        logging.info("Bot polling started: @%s (id=%s)", me_info.username, me_info.id)
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo

            from bot.keyboards import webapp_url

            url = webapp_url()
            if url:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="🚀 Открыть", web_app=WebAppInfo(url=url)
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logging.warning("Could not set chat menu button: %s", exc)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot_task: asyncio.Task | None = None
    if os.getenv("RUN_BOT", "1") == "1":
        bot_task = asyncio.create_task(_start_bot_polling(), name="aiogram-polling")
    try:
        yield
    finally:
        if bot_task is not None:
            bot_task.cancel()
            try:
                await bot_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass


app = FastAPI(title="Telegram Sales Mini App API", lifespan=lifespan)

origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in origins_env.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


for r in (me.router, catalog.router, cart.router, wallet.router, orders.router,
          reviews.router, courier.router, disputes.router, admin.router):
    app.include_router(r, prefix="/api")
