from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, require_admin
from api.notify import send_message
from api.schemas import (
    CityCreateIn,
    CityUpdateIn,
    CourierAssignIn,
    FreeCreditsIn,
    PaymentDecisionIn,
    PaymentOut,
    ProductCreateIn,
    ProductUpdateIn,
)
from api.utils import photo_to_url
from bot.models import (
    City,
    Order,
    OrderStatus,
    Payment,
    PaymentKind,
    PaymentStatus,
    Product,
    User,
)

router = APIRouter(dependencies=[Depends(require_admin)])


# ---------- cities ----------

@router.get("/admin/cities")
async def admin_cities(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(select(City).order_by(City.id))
    return [
        {
            "id": c.id,
            "name": c.name,
            "delivery_price_usdt": float(c.delivery_price_usdt or 0),
            "is_active": c.is_active,
        }
        for c in rows.scalars().all()
    ]


@router.post("/admin/cities")
async def create_city(body: CityCreateIn, session: AsyncSession = Depends(get_session)):
    city = City(name=body.name.strip(), delivery_price_usdt=body.delivery_price_usdt, is_active=True)
    session.add(city)
    try:
        await session.flush()
    except Exception as exc:
        raise HTTPException(400, f"Cannot create city: {exc}") from exc
    return {"id": city.id, "name": city.name, "delivery_price_usdt": float(city.delivery_price_usdt), "is_active": city.is_active}


@router.patch("/admin/cities/{city_id}")
async def update_city(city_id: int, body: CityUpdateIn, session: AsyncSession = Depends(get_session)):
    city = await session.get(City, city_id)
    if not city:
        raise HTTPException(404, "City not found")
    if body.name is not None:
        city.name = body.name.strip()
    if body.delivery_price_usdt is not None:
        city.delivery_price_usdt = body.delivery_price_usdt
    if body.is_active is not None:
        city.is_active = body.is_active
    await session.flush()
    return {"id": city.id, "name": city.name, "delivery_price_usdt": float(city.delivery_price_usdt), "is_active": city.is_active}


@router.delete("/admin/cities/{city_id}")
async def delete_city(city_id: int, session: AsyncSession = Depends(get_session)):
    city = await session.get(City, city_id)
    if not city:
        raise HTTPException(404, "City not found")
    await session.delete(city)
    await session.flush()
    return {"ok": True}


# ---------- products ----------

@router.get("/admin/products")
async def admin_products(
    session: AsyncSession = Depends(get_session),
    city_id: int | None = None,
):
    q = select(Product, City.name).join(City, City.id == Product.city_id)
    if city_id:
        q = q.where(Product.city_id == city_id)
    rows = await session.execute(q.order_by(Product.id))
    out = []
    for p, city_name in rows.all():
        out.append(
            {
                "id": p.id,
                "city_id": p.city_id,
                "city_name": city_name,
                "name": p.name,
                "description": p.description,
                "photo_url": photo_to_url(p.photo_file_id),
                "price_usdt": float(p.price_usdt or 0),
                "stock": p.stock,
                "is_active": p.is_active,
            }
        )
    return out


@router.post("/admin/products")
async def create_product(body: ProductCreateIn, session: AsyncSession = Depends(get_session)):
    if not await session.get(City, body.city_id):
        raise HTTPException(400, "City not found")
    product = Product(
        city_id=body.city_id,
        name=body.name.strip(),
        description=body.description.strip(),
        price_usdt=body.price_usdt,
        stock=body.stock,
        photo_file_id=body.photo_url,
        is_active=True,
    )
    session.add(product)
    await session.flush()
    return {"id": product.id}


@router.patch("/admin/products/{product_id}")
async def update_product(
    product_id: int,
    body: ProductUpdateIn,
    session: AsyncSession = Depends(get_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if body.name is not None:
        product.name = body.name.strip()
    if body.description is not None:
        product.description = body.description.strip()
    if body.price_usdt is not None:
        product.price_usdt = body.price_usdt
    if body.stock is not None:
        product.stock = body.stock
    if body.is_active is not None:
        product.is_active = body.is_active
    if body.photo_url is not None:
        product.photo_file_id = body.photo_url or None
    await session.flush()
    return {"ok": True}


@router.delete("/admin/products/{product_id}")
async def delete_product(product_id: int, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    await session.delete(product)
    await session.flush()
    return {"ok": True}


# ---------- couriers ----------

@router.get("/admin/couriers")
async def list_couriers(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(User, City.name)
        .join(City, City.id == User.courier_city_id, isouter=True)
        .where(User.courier_city_id.is_not(None))
        .order_by(User.id)
    )
    return [
        {
            "user_id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "city_id": u.courier_city_id,
            "city_name": city_name,
        }
        for u, city_name in rows.all()
    ]


@router.post("/admin/couriers")
async def assign_courier(body: CourierAssignIn, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, body.user_id)
    if not user:
        raise HTTPException(404, "User not found (they need to /start the bot first)")
    city = await session.get(City, body.city_id)
    if not city:
        raise HTTPException(404, "City not found")
    user.courier_city_id = city.id
    await session.flush()
    await send_message(user.id, f"🚴 Вас назначили курьером города <b>{city.name}</b>.")
    return {"ok": True}


@router.delete("/admin/couriers/{user_id}")
async def remove_courier(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.courier_city_id = None
    await session.flush()
    return {"ok": True}


# ---------- payments ----------

@router.get("/admin/payments")
async def admin_payments(
    session: AsyncSession = Depends(get_session),
    status: str | None = None,
):
    q = select(Payment, User.full_name).join(User, User.id == Payment.user_id)
    if status:
        try:
            q = q.where(Payment.status == PaymentStatus(status))
        except ValueError as exc:
            raise HTTPException(400, "Bad status") from exc
    else:
        q = q.where(Payment.status == PaymentStatus.PENDING_VERIFY)
    rows = await session.execute(q.order_by(Payment.id.desc()))
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "user_name": full_name,
            "kind": p.kind.value,
            "amount_usdt": float(p.amount_usdt or 0),
            "method": p.method.value,
            "txid": p.txid,
            "status": p.status.value,
            "created_at": p.created_at,
        }
        for p, full_name in rows.all()
    ]


@router.post("/admin/payments/{payment_id}/approve", response_model=PaymentOut)
async def approve_payment(
    payment_id: int,
    body: PaymentDecisionIn,
    session: AsyncSession = Depends(get_session),
):
    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    if payment.status != PaymentStatus.PENDING_VERIFY:
        raise HTTPException(400, "Payment not pending verify")
    payment.status = PaymentStatus.CONFIRMED
    payment.confirmed_at = datetime.now(UTC)
    user = await session.get(User, payment.user_id)
    if user is None:
        raise HTTPException(500, "User missing")

    if payment.kind == PaymentKind.TOPUP:
        user.balance_usdt = Decimal(str(user.balance_usdt or 0)) + Decimal(str(payment.amount_usdt))
        await send_message(
            user.id,
            f"✅ Пополнение #{payment.id} подтверждено.\nНа баланс зачислено <b>{payment.amount_usdt:.2f} USDT</b>.",
        )
    elif payment.kind == PaymentKind.ORDER_GROUP:
        rows = await session.execute(select(Order).where(Order.payment_id == payment.id))
        orders = list(rows.scalars().all())
        for o in orders:
            o.status = OrderStatus.PAID
            o.paid_at = datetime.now(UTC)
            res = await session.execute(
                select(User).where(User.courier_city_id == o.city_id).limit(1)
            )
            courier = res.scalars().first()
            if courier:
                o.courier_id = courier.id
                o.status = OrderStatus.IN_DELIVERY
                product = await session.get(Product, o.product_id)
                city = await session.get(City, o.city_id)
                await send_message(
                    courier.id,
                    f"🔔 <b>Новый заказ #{o.id}</b>\n"
                    f"Товар: {product.name if product else o.product_id}\n"
                    f"Город: {city.name if city else o.city_id}\n"
                    f"Адрес: {o.delivery_address}",
                )
        await send_message(
            user.id,
            f"✅ Платёж #{payment.id} подтверждён. Создано заказов: <b>{len(orders)}</b>.",
        )
    await session.flush()
    return PaymentOut.model_validate(payment)


@router.post("/admin/payments/{payment_id}/reject", response_model=PaymentOut)
async def reject_payment(
    payment_id: int,
    body: PaymentDecisionIn,
    session: AsyncSession = Depends(get_session),
):
    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    if payment.status not in {PaymentStatus.PENDING_VERIFY, PaymentStatus.PENDING_PAYMENT}:
        raise HTTPException(400, "Payment not in pending state")
    payment.status = PaymentStatus.REJECTED
    if payment.kind == PaymentKind.ORDER_GROUP:
        rows = await session.execute(select(Order).where(Order.payment_id == payment.id))
        for o in rows.scalars().all():
            o.status = OrderStatus.CANCELED
            product = await session.get(Product, o.product_id)
            if product is not None and product.stock >= 0:
                product.stock += 1
    await send_message(
        payment.user_id,
        f"❌ Платёж #{payment.id} отклонён. {body.note}".strip(),
    )
    await session.flush()
    return PaymentOut.model_validate(payment)


# ---------- free credits ----------

@router.post("/admin/free-credits")
async def grant_free_credits(body: FreeCreditsIn, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, body.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.free_credits = max(0, user.free_credits + body.amount)
    await session.flush()
    await send_message(user.id, f"🎁 Вам начислено бесплатных заказов: <b>{body.amount}</b>.")
    return {"ok": True, "free_credits": user.free_credits}
