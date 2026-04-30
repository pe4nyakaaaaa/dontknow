"""Диспуты: открытие покупателем, чат с модератором, разрешение."""

from __future__ import annotations

from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.config import settings
from bot.models import (
    Dispute,
    DisputeMessage,
    DisputeStatus,
    MessageKind,
    Order,
    OrderStatus,
    Product,
    User,
)
from bot.states import DisputeChatSG
from bot.utils import display_name, is_moderator

router = Router(name="disputes")


# ---------- открытие диспута покупателем ----------


@router.callback_query(F.data.startswith("dispute:open:"))
async def open_dispute(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext
) -> None:
    order_id = int(call.data.split(":")[2])
    order = await session.get(Order, order_id)
    if order is None or order.user_id != db_user.id:
        await call.answer("Заказ не найден", show_alert=True)
        return
    if order.status not in (OrderStatus.PAID, OrderStatus.IN_DELIVERY, OrderStatus.DELIVERED):
        await call.answer("По этому заказу диспут открыть нельзя", show_alert=True)
        return

    res = await session.execute(
        select(Dispute).where(Dispute.order_id == order.id, Dispute.status == DisputeStatus.OPEN)
    )
    if res.scalars().first() is not None:
        await call.answer("Диспут уже открыт", show_alert=True)
        return

    await state.set_state(DisputeChatSG.waiting_reason)
    await state.update_data(order_id=order.id)
    await call.message.answer(
        f"⚖️ <b>Открытие диспута по заказу #{order.id}</b>\n"
        f"{texts.LINE}\n"
        f"Опишите проблему одним сообщением — мы передадим её модератору."
    )
    await call.answer()


@router.message(DisputeChatSG.waiting_reason, F.text)
async def submit_dispute_reason(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, bot: Bot
) -> None:
    data = await state.get_data()
    order = await session.get(Order, int(data.get("order_id", 0)))
    if order is None or order.user_id != db_user.id:
        await state.clear()
        await message.answer("Заказ не найден.", reply_markup=kb.back_to_main_kb())
        return

    reason = (message.text or "").strip()
    if len(reason) < 5:
        await message.answer("Опишите проблему чуть подробнее.")
        return

    dispute = Dispute(
        order_id=order.id,
        buyer_id=db_user.id,
        reason=reason,
        status=DisputeStatus.OPEN,
    )
    session.add(dispute)
    order.status = OrderStatus.DISPUTED
    await session.flush()

    await state.set_state(DisputeChatSG.in_chat)
    await state.update_data(dispute_id=dispute.id)
    await message.answer(
        texts.DISPUTE_OPENED_BUYER.format(dispute_id=dispute.id, order_id=order.id),
        reply_markup=kb.in_dispute_chat_kb(dispute.id, is_moderator=False),
    )

    product = await session.get(Product, order.product_id)
    notify = texts.DISPUTE_FOR_MODS.format(
        dispute_id=dispute.id,
        line=texts.LINE,
        order_id=order.id,
        product=product.name if product else "—",
        buyer_id=db_user.id,
        buyer_name=display_name(db_user),
        reason=reason,
    )
    for mod_id in settings.moderator_ids:
        if mod_id == db_user.id:
            continue
        try:
            await bot.send_message(mod_id, notify, reply_markup=kb.dispute_take_kb(dispute.id))
        except Exception:
            pass


# ---------- модераторская сторона ----------


@router.callback_query(F.data == "mod:home")
async def mod_home(call: CallbackQuery) -> None:
    if not is_moderator(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return
    await call.message.edit_text(texts.MODERATOR_PANEL, reply_markup=kb.moderator_home_kb())
    await call.answer()


@router.callback_query(F.data == "mod:open")
async def mod_open_list(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_moderator(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return
    res = await session.execute(
        select(Dispute).where(Dispute.status == DisputeStatus.OPEN).order_by(Dispute.opened_at.desc())
    )
    disputes = list(res.scalars().all())
    if not disputes:
        await call.message.edit_text(
            texts.MODERATOR_PANEL + "\n📭 Открытых диспутов нет.",
            reply_markup=kb.moderator_home_kb(),
        )
    else:
        items = [(d.id, d.order_id) for d in disputes]
        await call.message.edit_text("⚖️ <b>Открытые диспуты:</b>", reply_markup=kb.disputes_list_kb(items))
    await call.answer()


@router.callback_query(F.data.startswith("mod:dispute:"))
async def mod_view_dispute(call: CallbackQuery, session: AsyncSession) -> None:
    if not is_moderator(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return
    dispute_id = int(call.data.split(":")[2])
    dispute = await session.get(Dispute, dispute_id)
    if dispute is None:
        await call.answer("Диспут не найден", show_alert=True)
        return
    order = await session.get(Order, dispute.order_id)
    product = await session.get(Product, order.product_id) if order else None
    buyer = await session.get(User, dispute.buyer_id)
    text = texts.DISPUTE_FOR_MODS.format(
        dispute_id=dispute.id,
        line=texts.LINE,
        order_id=dispute.order_id,
        product=product.name if product else "—",
        buyer_id=dispute.buyer_id,
        buyer_name=display_name(buyer),
        reason=dispute.reason,
    )
    await call.message.edit_text(text, reply_markup=kb.dispute_take_kb(dispute.id))
    await call.answer()


@router.callback_query(F.data.startswith("mod:take:"))
async def mod_take(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not is_moderator(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return
    dispute_id = int(call.data.split(":")[2])
    dispute = await session.get(Dispute, dispute_id)
    if dispute is None or dispute.status != DisputeStatus.OPEN:
        await call.answer("Диспут недоступен", show_alert=True)
        return
    if dispute.moderator_id is not None and dispute.moderator_id != db_user.id:
        await call.answer("Уже принят другим модератором", show_alert=True)
        return
    dispute.moderator_id = db_user.id
    await session.flush()

    await state.set_state(DisputeChatSG.in_chat)
    await state.update_data(dispute_id=dispute.id)
    await call.message.edit_text(
        f"🛡 Вы подключились к диспуту #{dispute.id}.\n"
        f"Все ваши сообщения и фото получит покупатель.",
        reply_markup=kb.in_dispute_chat_kb(dispute.id, is_moderator=True),
    )
    try:
        await bot.send_message(
            dispute.buyer_id,
            texts.DISPUTE_TAKEN_BUYER.format(dispute_id=dispute.id),
            reply_markup=kb.in_dispute_chat_kb(dispute.id, is_moderator=False),
        )
    except Exception:
        pass
    await call.answer()


# ---------- релэй сообщений диспута ----------


@router.callback_query(F.data == "dispute:exit", DisputeChatSG.in_chat)
async def dispute_exit(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.answer("🚪 Вы вышли из чата диспута.", reply_markup=kb.back_to_main_kb())
    await call.answer()


@router.message(DisputeChatSG.in_chat, F.text | F.photo)
async def dispute_relay(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    data = await state.get_data()
    dispute = await session.get(Dispute, int(data.get("dispute_id", 0)))
    if dispute is None or dispute.status != DisputeStatus.OPEN:
        await state.clear()
        await message.answer("Диспут закрыт.", reply_markup=kb.back_to_main_kb())
        return

    if message.from_user.id == dispute.buyer_id:
        recipient_id = dispute.moderator_id
        sender_label = f"👤 {display_name(db_user)}"
    elif message.from_user.id == dispute.moderator_id:
        recipient_id = dispute.buyer_id
        sender_label = "🛡 Модератор"
    else:
        await message.answer("Этот чат не для вас.")
        await state.clear()
        return

    if recipient_id is None:
        await message.answer("Модератор пока не подключён к диспуту.")
        return

    if message.photo:
        photo = message.photo[-1]
        caption = (message.caption or "").strip()
        session.add(DisputeMessage(
            dispute_id=dispute.id, sender_id=message.from_user.id,
            kind=MessageKind.PHOTO, text=caption or None, file_id=photo.file_id,
        ))
        try:
            await message.bot.send_photo(
                recipient_id, photo.file_id,
                caption=f"<b>{sender_label}</b>" + (f"\n{caption}" if caption else ""),
            )
        except Exception:
            await message.answer("⚠️ Не удалось доставить сообщение.")
        return

    text = (message.text or "").strip()
    if not text:
        return
    session.add(DisputeMessage(
        dispute_id=dispute.id, sender_id=message.from_user.id,
        kind=MessageKind.TEXT, text=text,
    ))
    try:
        await message.bot.send_message(recipient_id, f"<b>{sender_label}</b>\n{text}")
    except Exception:
        await message.answer("⚠️ Не удалось доставить сообщение.")


# ---------- разрешение диспута ----------


@router.callback_query(F.data.startswith("dispute:resolve_refund:"))
async def resolve_refund(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not is_moderator(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return
    dispute_id = int(call.data.split(":")[2])
    dispute = await session.get(Dispute, dispute_id)
    if dispute is None or dispute.status != DisputeStatus.OPEN:
        await call.answer("Диспут недоступен", show_alert=True)
        return
    dispute.status = DisputeStatus.RESOLVED_REFUND
    dispute.closed_at = datetime.now(UTC)

    order = await session.get(Order, dispute.order_id)
    if order is not None:
        order.status = OrderStatus.REFUNDED

    buyer = await session.get(User, dispute.buyer_id)
    if buyer is not None:
        buyer.free_credits += 1

    await session.flush()
    await state.clear()

    await call.message.edit_text(
        f"↩️ Диспут #{dispute.id} закрыт: возврат (бесплатный заказ начислен покупателю).",
        reply_markup=kb.moderator_home_kb(),
    )
    try:
        await bot.send_message(
            dispute.buyer_id,
            texts.DISPUTE_RESOLVED_REFUND.format(order_id=dispute.order_id),
            reply_markup=kb.back_to_main_kb(),
        )
    except Exception:
        pass
    await call.answer("Возврат оформлен")


@router.callback_query(F.data.startswith("dispute:resolve_reject:"))
async def resolve_reject(
    call: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    if not is_moderator(call.from_user.id):
        await call.answer("Доступ запрещён", show_alert=True)
        return
    dispute_id = int(call.data.split(":")[2])
    dispute = await session.get(Dispute, dispute_id)
    if dispute is None or dispute.status != DisputeStatus.OPEN:
        await call.answer("Диспут недоступен", show_alert=True)
        return
    dispute.status = DisputeStatus.RESOLVED_REJECTED
    dispute.closed_at = datetime.now(UTC)

    order = await session.get(Order, dispute.order_id)
    if order is not None and order.status == OrderStatus.DISPUTED:
        # возвращаем предыдущий статус: если уже была доставка — оставляем DELIVERED, иначе PAID
        order.status = OrderStatus.DELIVERED if order.delivered_at else OrderStatus.PAID

    await session.flush()
    await state.clear()

    await call.message.edit_text(
        f"❌ Диспут #{dispute.id} закрыт: отклонено.",
        reply_markup=kb.moderator_home_kb(),
    )
    try:
        await bot.send_message(
            dispute.buyer_id,
            texts.DISPUTE_RESOLVED_REJECT.format(order_id=dispute.order_id),
            reply_markup=kb.back_to_main_kb(),
        )
    except Exception:
        pass
    await call.answer("Отклонено")
