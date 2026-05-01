from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_session, require_courier
from api.notify import send_message
from api.schemas import ChatMessageOut, ChatSendIn
from bot.models import (
    ChatMessage,
    City,
    MessageKind,
    Order,
    OrderStatus,
    Product,
    User,
)

router = APIRouter()


@router.get("/courier/orders")
async def courier_orders(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_courier),
):
    """Возвращает заказы, относящиеся к курьеру:

    1. Все заказы, которые курьер уже взял (`courier_id == user.id`).
    2. Свободные оплаченные заказы (`status == PAID`, `courier_id IS NULL`)
       в городе, к которому курьер привязан — их можно «Принять».
    """
    rows = await session.execute(
        select(Order, Product.name, City.name)
        .join(Product, Product.id == Order.product_id)
        .join(City, City.id == Order.city_id)
        .where(
            or_(
                Order.courier_id == user.id,
                (Order.status == OrderStatus.PAID)
                & (Order.courier_id.is_(None))
                & (Order.city_id == user.courier_city_id),
            )
        )
        .order_by(Order.id.desc())
    )
    return [
        {
            "id": o.id,
            "status": o.status.value,
            "product_name": pn,
            "city_name": cn,
            "delivery_address": o.delivery_address,
            "total_usdt": float(o.total_usdt or 0),
            "created_at": o.created_at,
            "is_mine": o.courier_id == user.id,
        }
        for o, pn, cn in rows.all()
    ]


@router.post("/courier/orders/{order_id}/take")
async def take_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_courier),
):
    order = await session.get(Order, order_id)
    if order is None or order.city_id != user.courier_city_id:
        raise HTTPException(404, "Order not found")
    if order.status != OrderStatus.PAID or order.courier_id is not None:
        raise HTTPException(400, "Order is not available")
    order.courier_id = user.id
    order.status = OrderStatus.IN_DELIVERY
    await session.flush()
    await send_message(
        order.user_id,
        f"🚴 Курьер взял заказ #{order.id} в работу. Откройте чат, чтобы согласовать доставку.",
    )
    return {"ok": True}


@router.post("/courier/orders/{order_id}/deliver")
async def deliver_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_courier),
):
    order = await session.get(Order, order_id)
    if not order or order.courier_id != user.id:
        raise HTTPException(404, "Order not found")
    if order.status != OrderStatus.IN_DELIVERY:
        raise HTTPException(400, "Order not in delivery")
    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now(UTC)
    await session.flush()
    await send_message(order.user_id, f"📦 Заказ #{order.id} доставлен. Спасибо за покупку!")
    return {"ok": True}


@router.get("/orders/{order_id}/chat", response_model=list[ChatMessageOut])
async def chat_history(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if user.id not in {order.user_id, order.courier_id}:
        raise HTTPException(403, "Forbidden")
    rows = await session.execute(
        select(ChatMessage, User.full_name, User.username)
        .join(User, User.id == ChatMessage.sender_id)
        .where(ChatMessage.order_id == order_id)
        .order_by(ChatMessage.id.asc())
    )
    return [
        ChatMessageOut(
            id=m.id,
            sender_id=m.sender_id,
            sender_name=full_name or username or f"id{m.sender_id}",
            kind=m.kind.value,
            text=m.text,
            photo_url=m.file_id if m.file_id and m.file_id.startswith(("http", "/")) else None,
            created_at=m.created_at,
        )
        for m, full_name, username in rows.all()
    ]


@router.post("/orders/{order_id}/chat", response_model=ChatMessageOut)
async def chat_send(
    order_id: int,
    body: ChatSendIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if user.id not in {order.user_id, order.courier_id}:
        raise HTTPException(403, "Forbidden")
    if not body.text and not body.photo_data_url:
        raise HTTPException(400, "Empty message")
    msg = ChatMessage(
        order_id=order_id,
        sender_id=user.id,
        kind=MessageKind.PHOTO if body.photo_data_url else MessageKind.TEXT,
        text=body.text,
        file_id=body.photo_data_url,
    )
    session.add(msg)
    await session.flush()

    other_id = order.courier_id if user.id == order.user_id else order.user_id
    if other_id:
        preview = (body.text or "📷 Фото")[:200]
        await send_message(
            other_id,
            f"💬 <b>Сообщение по заказу #{order_id}</b>\n{preview}",
        )

    return ChatMessageOut(
        id=msg.id,
        sender_id=user.id,
        sender_name=user.full_name or user.username or f"id{user.id}",
        kind=msg.kind.value,
        text=msg.text,
        photo_url=msg.file_id if msg.file_id and msg.file_id.startswith(("http", "/")) else None,
        created_at=msg.created_at,
    )
