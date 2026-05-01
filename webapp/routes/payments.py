from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.database import get_session
from webapp.models import Payment, User
from webapp.routes.auth import get_current_user

router = APIRouter(prefix="/api/payments", tags=["payments"])

PAYMENT_METHODS = [
    {
        "id": "card",
        "name": "Банковская карта",
        "icon": "💳",
        "description": "Visa, Mastercard, МИР",
        "min_amount": 100,
        "max_amount": 100000,
        "commission": 0,
    },
    {
        "id": "crypto_btc",
        "name": "Bitcoin",
        "icon": "₿",
        "description": "Оплата в BTC",
        "min_amount": 500,
        "max_amount": 500000,
        "commission": 0,
    },
    {
        "id": "crypto_eth",
        "name": "Ethereum",
        "icon": "Ξ",
        "description": "Оплата в ETH",
        "min_amount": 500,
        "max_amount": 500000,
        "commission": 0,
    },
    {
        "id": "crypto_usdt",
        "name": "USDT (TRC-20)",
        "icon": "₮",
        "description": "Стейблкоин USDT",
        "min_amount": 100,
        "max_amount": 500000,
        "commission": 0,
    },
    {
        "id": "sbp",
        "name": "СБП",
        "icon": "🏦",
        "description": "Система быстрых платежей",
        "min_amount": 100,
        "max_amount": 100000,
        "commission": 0,
    },
    {
        "id": "qiwi",
        "name": "QIWI Кошелёк",
        "icon": "🟠",
        "description": "Пополнение через QIWI",
        "min_amount": 100,
        "max_amount": 50000,
        "commission": 2,
    },
    {
        "id": "youmoney",
        "name": "ЮMoney",
        "icon": "🟣",
        "description": "Яндекс Деньги / ЮMoney",
        "min_amount": 100,
        "max_amount": 50000,
        "commission": 2,
    },
    {
        "id": "skinpay",
        "name": "Оплата скинами",
        "icon": "🔫",
        "description": "Обмен скинов CS2 на баланс",
        "min_amount": 50,
        "max_amount": 1000000,
        "commission": 5,
    },
]


class DepositRequest(BaseModel):
    method: str
    amount: float


@router.get("/methods")
async def get_payment_methods():
    return PAYMENT_METHODS


@router.post("/deposit")
async def create_deposit(
    data: DepositRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    method_info = None
    for m in PAYMENT_METHODS:
        if m["id"] == data.method:
            method_info = m
            break
    if not method_info:
        raise HTTPException(400, "Неизвестный способ оплаты")
    if data.amount < method_info["min_amount"]:
        raise HTTPException(400, f"Минимальная сумма: {method_info['min_amount']} ₽")
    if data.amount > method_info["max_amount"]:
        raise HTTPException(400, f"Максимальная сумма: {method_info['max_amount']} ₽")

    payment = Payment(
        user_id=user.id,
        amount=data.amount,
        method=data.method,
        status="pending",
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    return {
        "payment_id": payment.id,
        "amount": payment.amount,
        "method": payment.method,
        "status": payment.status,
        "message": "Платёж создан. Ожидает подтверждения оператора.",
    }


@router.get("/history")
async def payment_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return [
        {
            "id": p.id,
            "amount": p.amount,
            "method": p.method,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]
