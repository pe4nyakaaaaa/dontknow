"""Общие хэндлеры: /start, главное меню."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.config import settings
from bot.models import User
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
