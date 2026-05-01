from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.schemas import MeOut
from bot.config import settings
from bot.models import User

router = APIRouter()


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user)) -> MeOut:
    return MeOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        balance_usdt=float(user.balance_usdt or 0),
        free_credits=user.free_credits,
        is_admin=settings.is_admin(user.id),
        is_moderator=settings.is_moderator(user.id),
        courier_city_id=user.courier_city_id,
    )
