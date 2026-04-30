"""Middleware: инжектирование AsyncSession и автосоздание пользователя в БД."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TgUser

from bot.db import async_session_maker
from bot.models import User, UserRole


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


class UserUpsertMiddleware(BaseMiddleware):
    """Создаёт/обновляет пользователя в БД для каждого update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = None
        if isinstance(event, Message):
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery):
            tg_user = event.from_user

        session = data.get("session")
        if tg_user is not None and session is not None:
            db_user = await session.get(User, tg_user.id)
            if db_user is None:
                db_user = User(
                    id=tg_user.id,
                    username=tg_user.username,
                    full_name=tg_user.full_name,
                    role=UserRole.USER,
                )
                session.add(db_user)
                await session.flush()
            else:
                if db_user.username != tg_user.username:
                    db_user.username = tg_user.username
                if db_user.full_name != tg_user.full_name:
                    db_user.full_name = tg_user.full_name
            data["db_user"] = db_user

        return await handler(event, data)
