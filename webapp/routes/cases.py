import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.database import get_session
from webapp.models import Case, CaseSkin, Skin, User, UserInventory
from webapp.routes.auth import get_current_user

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("/")
async def list_cases(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Case).order_by(Case.price))
    cases = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "price": c.price,
            "image_url": c.image_url,
            "description": c.description,
            "category": c.category,
        }
        for c in cases
    ]


@router.get("/{case_id}")
async def get_case(case_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Кейс не найден")

    skins_result = await session.execute(
        select(Skin, CaseSkin.drop_weight)
        .join(CaseSkin, CaseSkin.skin_id == Skin.id)
        .where(CaseSkin.case_id == case_id)
        .order_by(Skin.price.desc())
    )
    skins = [
        {
            "id": s.id,
            "name": s.name,
            "weapon": s.weapon,
            "rarity": s.rarity,
            "price": s.price,
            "color": s.color,
            "drop_weight": w,
        }
        for s, w in skins_result.all()
    ]

    return {
        "id": case.id,
        "name": case.name,
        "price": case.price,
        "image_url": case.image_url,
        "description": case.description,
        "category": case.category,
        "skins": skins,
    }


@router.post("/{case_id}/open")
async def open_case(
    case_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Кейс не найден")

    if user.balance < case.price:
        raise HTTPException(400, "Недостаточно средств на балансе")

    user.balance -= case.price
    user.balance = round(user.balance, 2)

    skins_result = await session.execute(
        select(Skin, CaseSkin.drop_weight)
        .join(CaseSkin, CaseSkin.skin_id == Skin.id)
        .where(CaseSkin.case_id == case_id)
    )
    items = skins_result.all()
    if not items:
        raise HTTPException(500, "В кейсе нет скинов")

    skins_list = [s for s, _ in items]
    weights = [w for _, w in items]
    won_skin = random.choices(skins_list, weights=weights, k=1)[0]

    inventory_item = UserInventory(
        user_id=user.id,
        skin_id=won_skin.id,
        obtained_from=case.name,
    )
    session.add(inventory_item)
    await session.commit()

    return {
        "won_skin": {
            "id": won_skin.id,
            "name": won_skin.name,
            "weapon": won_skin.weapon,
            "rarity": won_skin.rarity,
            "price": won_skin.price,
            "color": won_skin.color,
        },
        "new_balance": user.balance,
    }
