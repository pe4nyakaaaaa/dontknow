from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.database import get_session
from webapp.models import Skin, User, UserInventory
from webapp.routes.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/inventory")
async def get_inventory(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(UserInventory, Skin)
        .join(Skin, UserInventory.skin_id == Skin.id)
        .where(UserInventory.user_id == user.id)
        .order_by(UserInventory.obtained_at.desc())
    )
    items = result.all()
    return [
        {
            "inventory_id": inv.id,
            "skin": {
                "id": skin.id,
                "name": skin.name,
                "weapon": skin.weapon,
                "rarity": skin.rarity,
                "price": skin.price,
                "color": skin.color,
            },
            "obtained_at": inv.obtained_at.isoformat() if inv.obtained_at else None,
            "obtained_from": inv.obtained_from,
        }
        for inv, skin in items
    ]


@router.post("/sell/{inventory_id}")
async def sell_skin(
    inventory_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(UserInventory).where(
            UserInventory.id == inventory_id,
            UserInventory.user_id == user.id,
        )
    )
    inv_item = result.scalar_one_or_none()
    if not inv_item:
        raise HTTPException(404, "Предмет не найден в инвентаре")

    skin_result = await session.execute(select(Skin).where(Skin.id == inv_item.skin_id))
    skin = skin_result.scalar_one_or_none()
    if not skin:
        raise HTTPException(500, "Скин не найден")

    user.balance += skin.price
    user.balance = round(user.balance, 2)
    await session.delete(inv_item)
    await session.commit()

    return {"new_balance": user.balance, "sold_price": skin.price}
