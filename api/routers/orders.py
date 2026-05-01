from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_current_user, get_session
from api.notify import send_message
from api.schemas import (
    CheckoutIn,
    CheckoutOut,
    OrderDetailOut,
    OrderListItem,
)
from bot.config import settings
from bot.models import (
    CartItem,
    City,
    Order,
    OrderStatus,
    Payment,
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
    Product,
    User,
)

router = APIRouter()


async def _assign_courier_inplace(session: AsyncSession, order: Order) -> User | None:
    res = await session.execute(
        select(User).where(User.courier_city_id == order.city_id).limit(1)
    )
    courier = res.scalars().first()
    if courier:
        order.courier_id = courier.id
        order.status = OrderStatus.IN_DELIVERY
    return courier


@router.post("/checkout", response_model=CheckoutOut)
async def checkout(
    body: CheckoutIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CheckoutOut:
    res = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(selectinload(CartItem.product))
        .order_by(CartItem.added_at)
    )
    items = list(res.scalars().all())
    if not items:
        raise HTTPException(400, "Cart is empty")

    city_ids = []
    for it in items:
        if it.product.city_id not in city_ids:
            city_ids.append(it.product.city_id)
    cities_res = await session.execute(select(City).where(City.id.in_(city_ids)))
    cities = {c.id: c for c in cities_res.scalars().all()}

    address_map: dict[int, str] = {a.city_id: a.address.strip() for a in body.addresses if a.address}
    for cid in city_ids:
        if cid not in address_map or len(address_map[cid]) < 5:
            raise HTTPException(400, f"Missing or too short address for city {cid}")

    products_sum = Decimal("0")
    delivery_sum = Decimal("0")
    for it in items:
        products_sum += Decimal(str(it.product.price_usdt)) * it.quantity
    for cid in city_ids:
        delivery_sum += Decimal(str(cities[cid].delivery_price_usdt or 0))
    total = products_sum + delivery_sum

    method = body.method.upper()
    if method == PaymentMethod.BALANCE.value:
        if Decimal(str(user.balance_usdt or 0)) < total:
            raise HTTPException(400, "Not enough balance")
        user.balance_usdt = Decimal(str(user.balance_usdt or 0)) - total
        orders = await _create_orders(
            session, user, items, cities, address_map,
            paid=True, method=PaymentMethod.BALANCE,
        )
        await session.execute(delete(CartItem).where(CartItem.user_id == user.id))
        await session.flush()
        for o in orders:
            courier = await _assign_courier_inplace(session, o)
            if courier:
                await send_message(
                    courier.id,
                    f"🔔 <b>Новый заказ #{o.id}</b>\n"
                    f"Товар: {o.product.name if o.product else o.product_id}\n"
                    f"Город: {cities[o.city_id].name}\n"
                    f"Адрес: {o.delivery_address}",
                )
        await session.flush()
        return CheckoutOut(
            paid_from_balance=True,
            payment_id=None,
            order_ids=[o.id for o in orders],
            method=method,
        )

    if method not in {PaymentMethod.TON.value, PaymentMethod.USDT_TRC20.value}:
        raise HTTPException(400, "Bad method")

    payment = Payment(
        user_id=user.id,
        kind=PaymentKind.ORDER_GROUP,
        amount_usdt=total,
        method=PaymentMethod(method),
        status=PaymentStatus.PENDING_PAYMENT,
    )
    session.add(payment)
    await session.flush()

    orders = await _create_orders(
        session, user, items, cities, address_map,
        paid=False, method=PaymentMethod(method), payment_id=payment.id,
    )
    await session.execute(delete(CartItem).where(CartItem.user_id == user.id))
    await session.flush()

    wallet = settings.ton_wallet if method == "TON" else settings.usdt_trc20_wallet
    return CheckoutOut(
        paid_from_balance=False,
        payment_id=payment.id,
        order_ids=[o.id for o in orders],
        crypto_wallet=wallet or None,
        amount_usdt=float(total),
        method=method,
    )


async def _create_orders(
    session: AsyncSession,
    user: User,
    items: list[CartItem],
    cities: dict[int, City],
    addresses: dict[int, str],
    *,
    paid: bool,
    method: PaymentMethod,
    payment_id: int | None = None,
    free: bool = False,
) -> list[Order]:
    orders: list[Order] = []
    delivery_assigned: set[int] = set()
    for it in items:
        p = it.product
        for _ in range(it.quantity):
            unit_price = Decimal("0") if free else Decimal(str(p.price_usdt))
            order = Order(
                user_id=user.id,
                product_id=p.id,
                city_id=p.city_id,
                delivery_address=addresses.get(p.city_id),
                product_price_usdt=unit_price,
                delivery_price_usdt=Decimal("0"),
                total_usdt=unit_price,
                status=OrderStatus.PAID if paid else OrderStatus.AWAITING_PAYMENT,
                payment_method=method,
                payment_id=payment_id,
                is_free=free,
            )
            if paid:
                order.paid_at = datetime.now(UTC)
            if p.stock > 0:
                p.stock -= 1
            session.add(order)
            orders.append(order)
        if not free and p.city_id not in delivery_assigned:
            city = cities.get(p.city_id)
            if city is not None:
                delivery_amount = Decimal(str(city.delivery_price_usdt or 0))
                if delivery_amount > 0:
                    first = next(
                        (o for o in orders if o.city_id == p.city_id and o.delivery_price_usdt == Decimal("0")),
                        None,
                    )
                    if first is not None:
                        first.delivery_price_usdt = delivery_amount
                        first.total_usdt = Decimal(str(first.product_price_usdt)) + delivery_amount
                        delivery_assigned.add(p.city_id)
    await session.flush()
    return orders


@router.get("/orders", response_model=list[OrderListItem])
async def list_orders(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[OrderListItem]:
    rows = await session.execute(
        select(Order, Product.name, City.name)
        .join(Product, Product.id == Order.product_id)
        .join(City, City.id == Order.city_id)
        .where(Order.user_id == user.id)
        .order_by(Order.id.desc())
    )
    return [
        OrderListItem(
            id=o.id,
            status=o.status.value,
            product_name=p_name,
            city_name=c_name,
            total_usdt=float(o.total_usdt or 0),
            created_at=o.created_at,
        )
        for o, p_name, c_name in rows.all()
    ]


@router.get("/orders/{order_id}", response_model=OrderDetailOut)
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> OrderDetailOut:
    o = await session.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if o.user_id != user.id and o.courier_id != user.id and not settings.is_moderator(user.id):
        raise HTTPException(403, "Forbidden")
    product = await session.get(Product, o.product_id)
    city = await session.get(City, o.city_id)
    courier = await session.get(User, o.courier_id) if o.courier_id else None
    return OrderDetailOut(
        id=o.id,
        status=o.status.value,
        product_id=o.product_id,
        product_name=product.name if product else "",
        city_name=city.name if city else "",
        delivery_address=o.delivery_address,
        payment_method=o.payment_method.value if o.payment_method else None,
        product_price_usdt=float(o.product_price_usdt or 0),
        delivery_price_usdt=float(o.delivery_price_usdt or 0),
        total_usdt=float(o.total_usdt or 0),
        is_free=o.is_free,
        courier_id=o.courier_id,
        courier_name=courier.full_name if courier else None,
        created_at=o.created_at,
        paid_at=o.paid_at,
        delivered_at=o.delivered_at,
    )


@router.post("/orders/{order_id}/confirm-payment", response_model=OrderDetailOut)
async def confirm_external_payment(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> OrderDetailOut:
    """User pressed 'I paid' for a TON/USDT order. We just mark payment as PENDING_VERIFY."""
    o = await session.get(Order, order_id)
    if not o or o.user_id != user.id:
        raise HTTPException(404, "Order not found")
    if not o.payment_id:
        raise HTTPException(400, "Order has no external payment")
    payment = await session.get(Payment, o.payment_id)
    if payment and payment.status == PaymentStatus.PENDING_PAYMENT:
        payment.status = PaymentStatus.PENDING_VERIFY
        await session.flush()
    return await get_order(order_id, session, user)
