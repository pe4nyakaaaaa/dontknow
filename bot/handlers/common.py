"""Общие хэндлеры: /start, главное меню."""

from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.config import settings
from bot.models import (
    CartItem,
    ChatMessage,
    City,
    Dispute,
    DisputeMessage,
    Order,
    Payment,
    Product,
    Review,
    User,
)
from bot.utils import is_admin, is_courier, is_moderator

router = Router(name="common")


def _menu_kb(db_user: User | None) -> object:
    return kb.main_menu(
        is_admin=is_admin(db_user.id) if db_user else False,
        is_courier=is_courier(db_user),
        is_moderator=is_moderator(db_user.id) if db_user else False,
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: User, session: AsyncSession) -> None:
    await state.clear()
    text = texts.WELCOME.format(name=settings.bot_name, line=texts.LINE)
    await message.answer(text, reply_markup=_menu_kb(db_user))


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, db_user: User) -> None:
    await state.clear()
    await message.answer(
        texts.MAIN_MENU.format(line=texts.LINE),
        reply_markup=_menu_kb(db_user),
    )


@router.callback_query(F.data == "main")
async def cb_main(call: CallbackQuery, state: FSMContext, db_user: User) -> None:
    await state.clear()
    await call.message.edit_text(
        texts.MAIN_MENU.format(line=texts.LINE),
        reply_markup=_menu_kb(db_user),
    )
    await call.answer()


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>")


@router.message(Command("reset_data"))
async def cmd_reset_data(message: Message, session: AsyncSession) -> None:
    """OWNER-only: чистит транзакционные данные, оставляет пользователей и роли.

    Удаляет: чаты, диспуты, отзывы, заказы, корзины, платежи, товары, города.
    Сохраняет: пользователей (id/username/full_name/role/courier_city_id).
    Обнуляет: balance_usdt, free_credits.
    """
    if message.from_user.id != settings.owner_id:
        await message.answer("⛔️ Команда доступна только владельцу.")
        return
    # Порядок удалений учитывает FK ограничения.
    for tbl in (
        DisputeMessage,
        Dispute,
        ChatMessage,
        Review,
        Order,
        CartItem,
        Payment,
        Product,
        City,
    ):
        await session.execute(delete(tbl))
    # Курьеры могли быть привязаны к удалённым городам — обнуляем привязку,
    # чтобы потом админ перепривязал к новым.
    await session.execute(
        update(User).values(
            balance_usdt=Decimal("0"),
            free_credits=0,
            courier_city_id=None,
        )
    )
    await session.flush()
    await message.answer(
        "🧹 База очищена. Сохранены пользователи и admin/owner-роли. "
        "Балансы обнулены, курьеры отвязаны от городов (нужно перепривязать)."
    )
