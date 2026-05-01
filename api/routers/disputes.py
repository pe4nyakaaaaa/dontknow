from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_session, require_moderator
from api.notify import send_message
from api.schemas import (
    ChatMessageOut,
    ChatSendIn,
    DisputeOpenIn,
    DisputeOut,
    DisputeResolveIn,
)
from bot.config import settings
from bot.models import (
    Dispute,
    DisputeMessage,
    DisputeStatus,
    MessageKind,
    Order,
    OrderStatus,
    User,
)

router = APIRouter()


@router.post("/disputes", response_model=DisputeOut)
async def open_dispute(
    body: DisputeOpenIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    order = await session.get(Order, body.order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Order not found")
    existing = await session.scalar(
        select(Dispute).where(Dispute.order_id == order.id, Dispute.status == DisputeStatus.OPEN)
    )
    if existing:
        raise HTTPException(400, "Dispute already open")
    dispute = Dispute(order_id=order.id, buyer_id=user.id, reason=body.reason.strip())
    session.add(dispute)
    order.status = OrderStatus.DISPUTED
    await session.flush()
    for mid in settings.moderator_ids:
        await send_message(mid, f"⚖️ Открыт диспут #{dispute.id} по заказу #{order.id}.\nПричина: {body.reason}")
    return DisputeOut(
        id=dispute.id,
        order_id=order.id,
        status=dispute.status.value,
        reason=dispute.reason,
        moderator_id=None,
        moderator_name=None,
        opened_at=dispute.opened_at,
        closed_at=None,
    )


@router.get("/disputes", response_model=list[DisputeOut])
async def list_disputes(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    is_mod = settings.is_moderator(user.id)
    q = select(Dispute, User.full_name).join(User, User.id == Dispute.moderator_id, isouter=True)
    if not is_mod:
        q = q.where(Dispute.buyer_id == user.id)
    rows = await session.execute(q.order_by(Dispute.id.desc()))
    return [
        DisputeOut(
            id=d.id,
            order_id=d.order_id,
            status=d.status.value,
            reason=d.reason,
            moderator_id=d.moderator_id,
            moderator_name=mod_name,
            opened_at=d.opened_at,
            closed_at=d.closed_at,
        )
        for d, mod_name in rows.all()
    ]


@router.post("/disputes/{dispute_id}/take")
async def take_dispute(
    dispute_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_moderator),
):
    dispute = await session.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    if dispute.status != DisputeStatus.OPEN:
        raise HTTPException(400, "Dispute is not open")
    if dispute.moderator_id and dispute.moderator_id != user.id:
        raise HTTPException(400, "Already taken by another moderator")
    dispute.moderator_id = user.id
    await session.flush()
    await send_message(dispute.buyer_id, f"⚖️ К диспуту #{dispute.id} подключился модератор.")
    return {"ok": True}


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: int,
    body: DisputeResolveIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_moderator),
):
    dispute = await session.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    if dispute.status != DisputeStatus.OPEN:
        raise HTTPException(400, "Dispute already closed")
    dispute.status = DisputeStatus.RESOLVED_REFUND if body.refund else DisputeStatus.RESOLVED_REJECTED
    dispute.moderator_id = user.id
    dispute.closed_at = datetime.now(UTC)
    dispute.resolution_note = body.note.strip()
    if body.refund:
        buyer = await session.get(User, dispute.buyer_id)
        if buyer:
            buyer.free_credits += 1
        await send_message(
            dispute.buyer_id,
            f"🎁 Диспут #{dispute.id} решён в вашу пользу — начислен бесплатный заказ.",
        )
    else:
        await send_message(dispute.buyer_id, f"⚖️ Диспут #{dispute.id} закрыт без возмещения.")
    await session.flush()
    return {"ok": True}


@router.get("/disputes/{dispute_id}/chat", response_model=list[ChatMessageOut])
async def dispute_chat_history(
    dispute_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    dispute = await session.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    if dispute.buyer_id != user.id and not settings.is_moderator(user.id):
        raise HTTPException(403, "Forbidden")
    rows = await session.execute(
        select(DisputeMessage, User.full_name, User.username)
        .join(User, User.id == DisputeMessage.sender_id)
        .where(DisputeMessage.dispute_id == dispute_id)
        .order_by(DisputeMessage.id.asc())
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


@router.post("/disputes/{dispute_id}/chat", response_model=ChatMessageOut)
async def dispute_chat_send(
    dispute_id: int,
    body: ChatSendIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    dispute = await session.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    if dispute.buyer_id != user.id and not settings.is_moderator(user.id):
        raise HTTPException(403, "Forbidden")
    if not body.text and not body.photo_data_url:
        raise HTTPException(400, "Empty message")
    msg = DisputeMessage(
        dispute_id=dispute_id,
        sender_id=user.id,
        kind=MessageKind.PHOTO if body.photo_data_url else MessageKind.TEXT,
        text=body.text,
        file_id=body.photo_data_url,
    )
    session.add(msg)
    await session.flush()
    other_id = dispute.moderator_id if user.id == dispute.buyer_id else dispute.buyer_id
    if other_id:
        preview = (body.text or "📷 Фото")[:200]
        await send_message(other_id, f"💬 <b>Диспут #{dispute_id}</b>\n{preview}")
    return ChatMessageOut(
        id=msg.id,
        sender_id=user.id,
        sender_name=user.full_name or user.username or f"id{user.id}",
        kind=msg.kind.value,
        text=msg.text,
        photo_url=msg.file_id if msg.file_id and msg.file_id.startswith(("http", "/")) else None,
        created_at=msg.created_at,
    )
