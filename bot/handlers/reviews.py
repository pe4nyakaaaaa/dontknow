"""Отзывы: создание и просмотр."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot import keyboards as kb
from bot import texts
from bot.models import Order, OrderStatus, Review, User
from bot.states import ReviewSG
from bot.utils import display_name

router = Router(name="reviews")


@router.callback_query(F.data == "reviews:list")
async def list_reviews(call: CallbackQuery, session: AsyncSession) -> None:
    res = await session.execute(
        select(Review).options(selectinload(Review.user)).order_by(Review.created_at.desc()).limit(20)
    )
    reviews = list(res.scalars().all())
    if not reviews:
        await _safe_show(call, texts.REVIEWS_TITLE + "\n\n" + texts.NO_REVIEWS, kb.back_to_main_kb())
        await call.answer()
        return

    lines = [texts.REVIEWS_TITLE]
    for r in reviews:
        author = display_name(r.user)
        stars = "⭐" * r.rating
        body = r.text.strip() if r.text else ""
        lines.append(f"{stars}  <b>{author}</b>")
        if body:
            lines.append(f"<i>{body}</i>")
        lines.append(texts.LINE)
    text = "\n".join(lines).rstrip()
    await _safe_show(call, text, kb.back_to_main_kb())
    await call.answer()


async def _safe_show(call: CallbackQuery, text: str, markup) -> None:
    msg = call.message
    if msg.photo:
        try:
            await msg.delete()
        except Exception:
            pass
        await call.message.answer(text, reply_markup=markup)
    else:
        await msg.edit_text(text, reply_markup=markup)


@router.callback_query(F.data == "reviews:new")
async def new_review(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReviewSG.waiting_rating)
    await state.update_data(order_id=None)
    await call.message.edit_text(
        "✍️ <b>Новый отзыв</b>\n" + texts.LINE + "\nКакую оценку поставите?",
        reply_markup=kb.rating_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("reviews:for:"))
async def review_for_order(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext
) -> None:
    order_id = int(call.data.split(":")[2])
    order = await session.get(Order, order_id)
    if order is None or order.user_id != db_user.id:
        await call.answer("Заказ не найден", show_alert=True)
        return
    if order.status != OrderStatus.DELIVERED:
        await call.answer("Отзыв можно оставить только после доставки", show_alert=True)
        return
    await state.set_state(ReviewSG.waiting_rating)
    await state.update_data(order_id=order.id)
    await call.message.edit_text(
        f"✍️ <b>Отзыв по заказу #{order.id}</b>\n" + texts.LINE + "\nКакую оценку поставите?",
        reply_markup=kb.rating_kb(),
    )
    await call.answer()


@router.callback_query(ReviewSG.waiting_rating, F.data.startswith("review:rate:"))
async def picked_rating(call: CallbackQuery, state: FSMContext) -> None:
    rating = int(call.data.split(":")[2])
    if rating < 1 or rating > 5:
        await call.answer()
        return
    await state.update_data(rating=rating)
    await state.set_state(ReviewSG.waiting_text)
    await call.message.edit_text(
        f"Оценка: {'⭐' * rating}\n\nНапишите короткий комментарий или нажмите «✅ Без текста».",
        reply_markup=kb.review_skip_text_kb(),
    )
    await call.answer()


@router.callback_query(ReviewSG.waiting_text, F.data == "review:skip_text")
async def skip_review_text(
    call: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    await _save_review(call.message, state, session, db_user, body="")
    await call.answer("Спасибо за отзыв!")


@router.message(ReviewSG.waiting_text, F.text)
async def got_review_text(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    body = (message.text or "").strip()
    if len(body) > 500:
        await message.answer("Слишком длинно. Уложитесь в 500 символов.")
        return
    await _save_review(message, state, session, db_user, body=body)


async def _save_review(
    message_or_callmsg, state: FSMContext, session: AsyncSession, db_user: User, *, body: str
) -> None:
    data = await state.get_data()
    rating = int(data.get("rating", 5))
    order_id = data.get("order_id")
    review = Review(
        user_id=db_user.id,
        order_id=int(order_id) if order_id else None,
        rating=rating,
        text=body,
    )
    session.add(review)
    await session.flush()
    await state.clear()
    await message_or_callmsg.answer(
        "🌟 Спасибо! Ваш отзыв опубликован.",
        reply_markup=kb.back_to_main_kb(),
    )
