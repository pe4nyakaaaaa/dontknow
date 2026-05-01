from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from api.schemas import CityOut, ProductOut
from api.utils import photo_to_url
from bot.models import City, Product

router = APIRouter()


@router.get("/cities", response_model=list[CityOut])
async def list_cities(session: AsyncSession = Depends(get_session)) -> list[CityOut]:
    rows = await session.execute(
        select(City, func.count(Product.id))
        .join(Product, (Product.city_id == City.id) & (Product.is_active.is_(True)), isouter=True)
        .where(City.is_active.is_(True))
        .group_by(City.id)
        .order_by(City.name.asc())
    )
    return [
        CityOut(
            id=c.id,
            name=c.name,
            delivery_price_usdt=float(c.delivery_price_usdt or 0),
            is_active=c.is_active,
            products_count=count,
        )
        for c, count in rows.all()
    ]


@router.get("/cities/{city_id}/products", response_model=list[ProductOut])
async def city_products(city_id: int, session: AsyncSession = Depends(get_session)) -> list[ProductOut]:
    city = await session.get(City, city_id)
    if not city:
        raise HTTPException(404, "City not found")
    rows = await session.execute(
        select(Product).where(Product.city_id == city_id, Product.is_active.is_(True)).order_by(Product.name.asc())
    )
    products = rows.scalars().all()
    return [
        ProductOut(
            id=p.id,
            city_id=city.id,
            city_name=city.name,
            name=p.name,
            description=p.description,
            photo_url=photo_to_url(p.photo_file_id),
            price_usdt=float(p.price_usdt or 0),
            stock=p.stock,
            is_active=p.is_active,
        )
        for p in products
    ]


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)) -> ProductOut:
    p = await session.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    city = await session.get(City, p.city_id)
    return ProductOut(
        id=p.id,
        city_id=p.city_id,
        city_name=city.name if city else "",
        name=p.name,
        description=p.description,
        photo_url=photo_to_url(p.photo_file_id),
        price_usdt=float(p.price_usdt or 0),
        stock=p.stock,
        is_active=p.is_active,
    )
