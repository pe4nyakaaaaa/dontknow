from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.database import get_session
from webapp.models import SupportMessage, SupportTicket, User
from webapp.routes.auth import get_current_user

router = APIRouter(prefix="/api/support", tags=["support"])


class CreateTicketRequest(BaseModel):
    subject: str
    message: str


class SendMessageRequest(BaseModel):
    message: str


FAQ_ITEMS = [
    {
        "question": "Как пополнить баланс?",
        "answer": "Перейдите в раздел «Пополнение», выберите способ оплаты и следуйте инструкциям. Средства зачисляются после подтверждения.",
    },
    {
        "question": "Как открыть кейс?",
        "answer": "Выберите кейс на главной странице, нажмите «Открыть». Стоимость кейса спишется с баланса, а выигранный скин появится в инвентаре.",
    },
    {
        "question": "Как продать скин?",
        "answer": "Откройте инвентарь в профиле и нажмите «Продать» рядом с нужным скином. Сумма будет зачислена на баланс.",
    },
    {
        "question": "Что такое Case Battle?",
        "answer": "Case Battle — режим, где два игрока одновременно открывают кейсы. Тот, кто получит более дорогой скин, забирает все предметы.",
    },
    {
        "question": "Как вывести скины?",
        "answer": "Раздел вывода находится в профиле. Выберите скины для вывода и укажите Trade URL вашего Steam-аккаунта.",
    },
    {
        "question": "Честная ли рулетка?",
        "answer": "Да! Мы используем систему Provably Fair — каждый результат можно проверить. Хэш раунда публикуется заранее.",
    },
    {
        "question": "Как связаться с поддержкой?",
        "answer": "Создайте тикет в разделе «Техподдержка». Среднее время ответа — 15 минут. Также можно написать в Telegram.",
    },
    {
        "question": "Безопасен ли сайт?",
        "answer": "Все пароли хешируются, данные передаются по HTTPS. Мы не храним данные банковских карт.",
    },
]


@router.get("/faq")
async def get_faq():
    return FAQ_ITEMS


@router.post("/tickets")
async def create_ticket(
    data: CreateTicketRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not data.subject.strip():
        raise HTTPException(400, "Тема не может быть пустой")
    if not data.message.strip():
        raise HTTPException(400, "Сообщение не может быть пустым")
    if len(data.subject) > 300:
        raise HTTPException(400, "Тема слишком длинная (макс. 300 символов)")

    ticket = SupportTicket(user_id=user.id, subject=data.subject[:300])
    session.add(ticket)
    await session.flush()

    msg = SupportMessage(
        ticket_id=ticket.id,
        user_id=user.id,
        message=data.message[:2000],
        is_admin=False,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(ticket)

    return {
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
    }


@router.get("/tickets")
async def list_tickets(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.created_at.desc())
    )
    tickets = result.scalars().all()
    return [
        {
            "id": t.id,
            "subject": t.subject,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tickets
    ]


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Тикет не найден")

    msgs_result = await session.execute(
        select(SupportMessage)
        .where(SupportMessage.ticket_id == ticket_id)
        .order_by(SupportMessage.created_at)
    )
    messages = msgs_result.scalars().all()

    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "messages": [
            {
                "id": m.id,
                "message": m.message,
                "is_admin": m.is_admin,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.post("/tickets/{ticket_id}/message")
async def send_message(
    ticket_id: int,
    data: SendMessageRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Тикет не найден")
    if ticket.status == "closed":
        raise HTTPException(400, "Тикет закрыт")

    if not data.message.strip():
        raise HTTPException(400, "Сообщение не может быть пустым")

    msg = SupportMessage(
        ticket_id=ticket.id,
        user_id=user.id,
        message=data.message[:2000],
        is_admin=False,
    )
    session.add(msg)
    await session.commit()

    return {"status": "ok"}
