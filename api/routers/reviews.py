from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_session
from api.schemas import ReviewCreateIn, ReviewOut
from bot.models import Order, OrderStatus, Review, User

router = APIRouter()


@router.get("/reviews", response_model=list[ReviewOut])
async def list_reviews(session: AsyncSession = Depends(get_session)) -> list[ReviewOut]:
    rows = await session.execute(
        select(Review, User.full_name, User.username)
        .join(User, User.id == Review.user_id)
        .order_by(Review.id.desc())
        .limit(200)
    )
    out: list[ReviewOut] = []
    for r, full_name, username in rows.all():
        out.append(
            ReviewOut(
                id=r.id,
                user_name=full_name or username or f"id{r.user_id}",
                rating=r.rating,
                text=r.text,
                created_at=r.created_at,
            )
        )
    return out


@router.post("/reviews", response_model=ReviewOut)
async def create_review(
    body: ReviewCreateIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReviewOut:
    if not 1 <= body.rating <= 5:
        raise HTTPException(400, "Rating must be 1..5")
    order = await session.get(Order, body.order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Order not found")
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(400, "Only delivered orders can be reviewed")
    review = Review(user_id=user.id, order_id=order.id, rating=body.rating, text=body.text.strip())
    session.add(review)
    await session.flush()
    return ReviewOut(
        id=review.id,
        user_name=user.full_name or user.username or f"id{user.id}",
        rating=review.rating,
        text=review.text,
        created_at=review.created_at,
    )
