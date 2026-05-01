"""FastAPI dependencies."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.init_data import InitDataError, parse_init_data
from bot.config import settings
from bot.db import async_session_maker
from bot.models import User, UserRole


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _allow_dev_bypass() -> int | None:
    """For local dev only: if DEV_USER_ID is set, skip initData validation."""
    raw = os.getenv("DEV_USER_ID")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
) -> User:
    init_data: str | None = None
    if authorization and authorization.lower().startswith("tma "):
        init_data = authorization[4:].strip()
    elif x_init_data:
        init_data = x_init_data.strip()

    dev_id = _allow_dev_bypass()
    if not init_data and dev_id is not None:
        user_id = dev_id
        username = "dev"
        full_name = "Dev User"
    else:
        if not init_data:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing initData")
        try:
            parsed = parse_init_data(init_data, settings.bot_token)
        except InitDataError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid initData: {exc}") from exc
        user_id = parsed.user.id
        username = parsed.user.username
        full_name = parsed.user.full_name

    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=username, full_name=full_name, role=UserRole.USER)
        session.add(user)
        await session.flush()
    else:
        if username and user.username != username:
            user.username = username
        if full_name and user.full_name != full_name:
            user.full_name = full_name
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not settings.is_admin(user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


def require_moderator(user: User = Depends(get_current_user)) -> User:
    if not settings.is_moderator(user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Moderator only")
    return user


def require_courier(user: User = Depends(get_current_user)) -> User:
    if user.courier_city_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Courier only")
    return user
