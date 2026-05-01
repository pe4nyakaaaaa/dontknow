from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_session
from api.schemas import PaymentOut, TopupCreateIn, TopupSubmitTxIn, WalletOut
from bot.config import settings
from bot.models import Payment, PaymentKind, PaymentMethod, PaymentStatus, User

router = APIRouter()


@router.get("/wallet", response_model=WalletOut)
async def get_wallet(user: User = Depends(get_current_user)) -> WalletOut:
    return WalletOut(balance_usdt=float(user.balance_usdt or 0), free_credits=user.free_credits)


@router.get("/wallet/payments", response_model=list[PaymentOut])
async def list_payments(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[PaymentOut]:
    rows = await session.execute(
        select(Payment).where(Payment.user_id == user.id).order_by(Payment.id.desc())
    )
    return [PaymentOut.model_validate(p) for p in rows.scalars().all()]


@router.post("/wallet/topup", response_model=PaymentOut)
async def create_topup(
    body: TopupCreateIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    if body.amount_usdt <= 0:
        raise HTTPException(400, "Amount must be positive")
    method = body.method.upper()
    if method not in {PaymentMethod.TON.value, PaymentMethod.USDT_TRC20.value}:
        raise HTTPException(400, "Bad method")
    payment = Payment(
        user_id=user.id,
        kind=PaymentKind.TOPUP,
        amount_usdt=body.amount_usdt,
        method=PaymentMethod(method),
        status=PaymentStatus.PENDING_PAYMENT,
    )
    session.add(payment)
    await session.flush()
    return PaymentOut.model_validate(payment)


@router.post("/wallet/payments/{payment_id}/tx", response_model=PaymentOut)
async def submit_tx(
    payment_id: int,
    body: TopupSubmitTxIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    payment = await session.get(Payment, payment_id)
    if not payment or payment.user_id != user.id:
        raise HTTPException(404, "Payment not found")
    if payment.status != PaymentStatus.PENDING_PAYMENT:
        raise HTTPException(400, "Payment already submitted")
    payment.txid = body.txid.strip()
    payment.status = PaymentStatus.PENDING_VERIFY
    await session.flush()
    return PaymentOut.model_validate(payment)


@router.get("/wallet/crypto-addresses")
async def crypto_addresses() -> dict[str, str]:
    return {
        "TON": settings.ton_wallet or "",
        "USDT_TRC20": settings.usdt_trc20_wallet or "",
    }
