"""Доставка: назначение курьера, чат покупатель ↔ курьер, статус «Доставлено»."""

from __future__ import annotations

from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.models import ChatMessage, MessageKind, Order, OrderStatus, Product, User
from bot.states import ChatSG
from bot.utils import display_name

router = Router(name="delivery")


# ---------- назначение курьера ----------


async def assign_courier_and_notify(bot: Bot, session: AsyncSession, order: Order) -> None:
    """Ищем курьера, привязанного к городу заказа, уведомляем."""
    res = await session.execute(select(User).where(User.courier_city_id == order.city_id))
    courier = res.scalars().first()
    if courier is None:
        try:
            await bot.send_message(order.user_id, texts.NO_COURIER_FOR_CITY)
        except Exception:
            pass
        return

    order.courier_id = courier.id
    await session.flush()

    product = await session.get(Product, order.product_id)
    text = texts.ORDER_ASSIGNED_COURIER.format(
        order_id=order.id,
        line=texts.LINE,
        product=product.name if product else "—",
        city=order.city.name if order.city else "—",
        address=order.delivery_address or "—",
    )
    try:
        await bot.send_message(courier.id, text, reply_markup=kb.order_view_kb(order, is_courier_view=True))
    except Exception:
        pass


# ---------- курьерский кабинет ----------


@router.callback_query(F.data == "courier:home")
async def courier_home(call: CallbackQuery, db_user: User) -> None:
    if db_user.courier_city_id is None:
        await call.answer("Вы не курьер", show_alert=True)
        return
    await _safe_edit(call, texts.COURIER_PANEL, kb.courier_home_kb())
    await call.answer()


@router.callback_query(F.data == "courier:active")
async def courier_active(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    if db_user.courier_city_id is None:
        await call.answer("Вы не курьер", show_alert=True)
        return
    res = await session.execute(
        select(Order)
        .where(
            Order.city_id == db_user.courier_city_id,
            Order.status.in_((OrderStatus.PAID, OrderStatus.IN_DELIVERY)),
        )
        .order_by(Order.created_at.desc())
    )
    orders = list(res.scalars().all())
    if not orders:
        await _safe_edit(call, "📭 Активных заказов нет.", kb.courier_home_kb())
    else:
        await _safe_edit(call, "📦 <b>Активные заказы:</b>", kb.orders_list_kb(orders))
    await call.answer()


@router.callback_query(F.data == "courier:history")
async def courier_history(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    if db_user.courier_city_id is None:
        await call.answer()
        return
    res = await session.execute(
        select(Order)
        .where(
            Order.courier_id == db_user.id,
            Order.status.in_((OrderStatus.DELIVERED, OrderStatus.REFUNDED, OrderStatus.CANCELED)),
        )
        .order_by(Order.created_at.desc())
        .limit(30)
    )
    orders = list(res.scalars().all())
    if not orders:
        await _safe_edit(call, "📭 История пуста.", kb.courier_home_kb())
    else:
        await _safe_edit(call, "📜 <b>История доставок:</b>", kb.orders_list_kb(orders))
    await call.answer()


@router.callback_query(F.data.startswith("courier:take:"))
async def courier_take(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    order_id = int(call.data.split(":")[2])
    order = await session.get(Order, order_id)
    if order is None or order.city_id != db_user.courier_city_id:
        await call.answer("Заказ недоступен", show_alert=True)
        return
    if order.status != OrderStatus.PAID:
        await call.answer("Заказ нельзя взять", show_alert=True)
        return
    order.courier_id = db_user.id
    order.status = OrderStatus.IN_DELIVERY
    await session.flush()

    product = await session.get(Product, order.product_id)
    text = texts.order_summary(
        order.id,
        product.name if product else "—",
        order.city.name if order.city else "—",
        order.total_usdt,
        texts.status_label(order.status.value),
    ) + f"\n📍 <code>{order.delivery_address}</code>"
    await _safe_edit(call, text, kb.order_view_kb(order, is_courier_view=True))

    try:
        await call.bot.send_message(
            order.user_id,
            f"🚴 Курьер взял заказ #{order.id} в работу.\n"
            f"Откройте чат, чтобы согласовать детали доставки.",
            reply_markup=kb.order_view_kb(order),
        )
    except Exception:
        pass
    await call.answer("Заказ взят!")


@router.callback_query(F.data.startswith("courier:deliver:"))
async def courier_deliver(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext
) -> None:
    order_id = int(call.data.split(":")[2])
    order = await session.get(Order, order_id)
    if order is None or order.courier_id != db_user.id:
        await call.answer("Заказ не ваш", show_alert=True)
        return
    if order.status != OrderStatus.IN_DELIVERY:
        await call.answer("Нельзя завершить заказ в этом статусе", show_alert=True)
        return
    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now(UTC)
    await session.flush()
    await state.clear()

    await _safe_edit(call, f"📦 Заказ #{order.id} помечен как доставленный.", kb.courier_home_kb())
    try:
        await call.bot.send_message(
            order.user_id,
            f"📦 Заказ #{order.id} доставлен. Спасибо за покупку!\n"
            f"Поделитесь впечатлениями — оставьте отзыв 🌟",
            reply_markup=kb.order_view_kb(order),
        )
    except Exception:
        pass
    await call.answer("Готово!")


# ---------- чат покупатель ↔ курьер ----------


@router.callback_query(F.data.startswith("chat:open:"))
async def open_chat(call: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    order_id = int(call.data.split(":")[2])
    order = await session.get(Order, order_id)
    if order is None:
        await call.answer("Заказ не найден", show_alert=True)
        return
    if call.from_user.id not in (order.user_id, order.courier_id):
        await call.answer("Этот чат не для вас", show_alert=True)
        return
    if order.status != OrderStatus.IN_DELIVERY:
        await call.answer("Чат доступен только в процессе доставки", show_alert=True)
        return

    await state.set_state(ChatSG.in_chat)
    await state.update_data(order_id=order.id)
    await call.message.answer(texts.CHAT_OPENED.format(order_id=order.id), reply_markup=kb.in_chat_kb())
    await call.answer()


@router.callback_query(F.data == "chat:exit", ChatSG.in_chat)
async def exit_chat(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.answer(texts.CHAT_CLOSED, reply_markup=kb.back_to_main_kb())
    await call.answer()


@router.message(ChatSG.in_chat, F.text | F.photo)
async def relay_message(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    data = await state.get_data()
    order_id = int(data.get("order_id", 0))
    order = await session.get(Order, order_id)
    if order is None:
        await state.clear()
        await message.answer("Заказ закрыт.", reply_markup=kb.back_to_main_kb())
        return
    if order.status != OrderStatus.IN_DELIVERY:
        await state.clear()
        await message.answer("Чат больше недоступен.", reply_markup=kb.back_to_main_kb())
        return

    if message.from_user.id == order.user_id:
        recipient_id = order.courier_id
        sender_label = f"👤 {display_name(db_user)}"
    elif message.from_user.id == order.courier_id:
        recipient_id = order.user_id
        sender_label = "🚴 Курьер"
    else:
        await message.answer("Этот чат не для вас.")
        await state.clear()
        return

    if recipient_id is None:
        await message.answer("Собеседник пока не подключён.")
        return

    if message.photo:
        photo = message.photo[-1]
        caption = (message.caption or "").strip()
        session.add(ChatMessage(
            order_id=order.id, sender_id=message.from_user.id,
            kind=MessageKind.PHOTO, text=caption or None, file_id=photo.file_id,
        ))
        try:
            await message.bot.send_photo(
                recipient_id, photo.file_id,
                caption=f"<b>{sender_label}</b>" + (f"\n{caption}" if caption else ""),
            )
        except Exception:
            await message.answer("⚠️ Не удалось доставить сообщение собеседнику.")
        return

    text = (message.text or "").strip()
    if not text:
        return
    session.add(ChatMessage(
        order_id=order.id, sender_id=message.from_user.id,
        kind=MessageKind.TEXT, text=text,
    ))
    try:
        await message.bot.send_message(recipient_id, f"<b>{sender_label}</b>\n{text}")
    except Exception:
        await message.answer("⚠️ Не удалось доставить сообщение собеседнику.")


async def _safe_edit(call: CallbackQuery, text: str, markup) -> None:
    msg = call.message
    if msg.photo:
        try:
            await msg.delete()
        except Exception:
            pass
        await call.message.answer(text, reply_markup=markup)
    else:
        await msg.edit_text(text, reply_markup=markup)
