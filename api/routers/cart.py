from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_session
from api.schemas import CartAddIn, CartItemOut, CartOut, CartUpdateIn
from api.utils import photo_to_url
from bot.models import CartItem, City, Product, User

router = APIRouter()


async def _serialize_cart(session: AsyncSession, user: User) -> CartOut:
    rows = await session.execute(
        select(CartItem, Product, City)
        .join(Product, Product.id == CartItem.product_id)
        .join(City, City.id == Product.city_id)
        .where(CartItem.user_id == user.id)
        .order_by(CartItem.added_at.asc())
    )
    items: list[CartItemOut] = []
    items_total = 0.0
    delivery_seen: dict[int, float] = {}
    for ci, p, c in rows.all():
        price = float(p.price_usdt or 0)
        items.append(
            CartItemOut(
                id=ci.id,
                product_id=p.id,
                product_name=p.name,
                city_id=c.id,
                city_name=c.name,
                price_usdt=price,
                delivery_price_usdt=float(c.delivery_price_usdt or 0),
                quantity=ci.quantity,
                photo_url=photo_to_url(p.photo_file_id),
            )
        )
        items_total += price * ci.quantity
        delivery_seen[c.id] = float(c.delivery_price_usdt or 0)
    delivery_total = sum(delivery_seen.values())
    return CartOut(
        items=items,
        items_total_usdt=round(items_total, 2),
        delivery_total_usdt=round(delivery_total, 2),
        total_usdt=round(items_total + delivery_total, 2),
    )


@router.get("/cart", response_model=CartOut)
async def get_cart(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CartOut:
    return await _serialize_cart(session, user)


@router.post("/cart/items", response_model=CartOut)
async def add_to_cart(
    body: CartAddIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CartOut:
    product = await session.get(Product, body.product_id)
    if not product or not product.is_active:
        raise HTTPException(404, "Product not found")
    qty = max(1, body.quantity)
    existing = await session.scalar(
        select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product.id)
    )
    if existing:
        existing.quantity += qty
    else:
        session.add(CartItem(user_id=user.id, product_id=product.id, quantity=qty))
    await session.flush()
    return await _serialize_cart(session, user)


@router.patch("/cart/items/{item_id}", response_model=CartOut)
async def update_cart_item(
    item_id: int,
    body: CartUpdateIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CartOut:
    item = await session.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Cart item not found")
    if body.quantity <= 0:
        await session.delete(item)
    else:
        item.quantity = body.quantity
    await session.flush()
    return await _serialize_cart(session, user)


@router.delete("/cart/items/{item_id}", response_model=CartOut)
async def remove_cart_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CartOut:
    item = await session.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Cart item not found")
    await session.delete(item)
    await session.flush()
    return await _serialize_cart(session, user)


@router.delete("/cart", response_model=CartOut)
async def clear_cart(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CartOut:
    await session.execute(delete(CartItem).where(CartItem.user_id == user.id))
    await session.flush()
    return await _serialize_cart(session, user)
