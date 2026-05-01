"""SQLAlchemy engine и async-сессии."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings
from bot.models import Base

engine = create_async_engine(settings.database_url, echo=settings.sql_echo, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Дополнения схемы: пары (table, column, ddl). На SQLite добавляем колонку
# через `ALTER TABLE ... ADD COLUMN` — идемпотентно, ошибки «duplicate column»
# поглощаем. create_all не умеет добавлять колонки в существующие таблицы.
_PENDING_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("orders", "stock_consumed", "BOOLEAN NOT NULL DEFAULT 0"),
)


async def _apply_pending_alters() -> None:
    async with engine.begin() as conn:
        for table, column, ddl in _PENDING_COLUMNS:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                logging.info("Migration: added %s.%s", table, column)
            except Exception as exc:  # noqa: BLE001
                msg = str(exc).lower()
                if "duplicate" in msg or "already exists" in msg:
                    continue
                logging.warning("Migration ALTER %s.%s failed: %s", table, column, exc)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _apply_pending_alters()


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Удобный контекстный менеджер для разовых операций вне middleware."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
