"""Утилиты: проверки ролей, форматтеры, декоратор."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models import User


def display_name(user: User | None) -> str:
    if user is None:
        return "Пользователь"
    if user.full_name:
        return user.full_name
    if user.username:
        return f"@{user.username}"
    return f"id{user.id}"


def is_admin(user_id: int) -> bool:
    return settings.is_admin(user_id)


def is_moderator(user_id: int) -> bool:
    return settings.is_moderator(user_id)


def is_courier(user: User | None) -> bool:
    return user is not None and user.courier_city_id is not None


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def list_couriers(session: AsyncSession) -> list[User]:
    res = await session.execute(select(User).where(User.courier_city_id.is_not(None)))
    return list(res.scalars().all())
