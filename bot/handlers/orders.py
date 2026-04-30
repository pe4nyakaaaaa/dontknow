"""История и просмотр заказов."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.models import Order, Product, User

router = Router(name="orders")


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


@router.callback_query(F.data == "orders:list")
async def list_orders(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    res = await session.execute(
        select(Order).where(Order.user_id == db_user.id).order_by(Order.created_at.desc()).limit(30)
    )
    orders = list(res.scalars().all())
    if not orders:
        await _safe_show(call, texts.ORDER_HISTORY_TITLE + "\n\n" + texts.NO_ORDERS, kb.back_to_main_kb())
    else:
        await _safe_show(call, texts.ORDER_HISTORY_TITLE, kb.orders_list_kb(orders))
    await call.answer()


@router.callback_query(F.data.startswith("orders:view:"))
async def view_order(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    order_id = int(call.data.split(":")[2])
    order = await session.get(Order, order_id)
    if order is None:
        await call.answer("Заказ не найден", show_alert=True)
        return
    is_courier_view = order.courier_id == db_user.id and order.user_id != db_user.id
    if order.user_id != db_user.id and not is_courier_view:
        await call.answer("Заказ не ваш", show_alert=True)
        return
    product = await session.get(Product, order.product_id)
    text = texts.order_summary(
        order.id,
        product.name if product else "—",
        order.city.name if order.city else "—",
        order.total_usdt,
        texts.status_label(order.status.value),
    )
    if order.delivery_address:
        text += f"\n📍 Адрес: <code>{order.delivery_address}</code>"
    await _safe_show(call, text, kb.order_view_kb(order, is_courier_view=is_courier_view))
    await call.answer()
