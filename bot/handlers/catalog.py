"""Каталог: список городов, товаров, карточка товара."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.models import City, Product

router = Router(name="catalog")


async def _safe_show(call: CallbackQuery, text: str, markup) -> None:
    """Если предыдущее сообщение — фото, edit_text не сработает: удалим и пришлём заново."""
    msg = call.message
    if msg.photo:
        try:
            await msg.delete()
        except Exception:
            pass
        await call.message.answer(text, reply_markup=markup)
    else:
        await msg.edit_text(text, reply_markup=markup)


async def _list_cities(session: AsyncSession) -> list[City]:
    res = await session.execute(select(City).where(City.is_active.is_(True)).order_by(City.name))
    return list(res.scalars().all())


@router.callback_query(F.data == "catalog:cities")
async def show_cities(call: CallbackQuery, session: AsyncSession) -> None:
    cities = await _list_cities(session)
    if not cities:
        await _safe_show(call, texts.NO_CITIES, kb.back_to_main_kb())
    else:
        await _safe_show(call, texts.CITIES_TITLE, kb.cities_kb(cities))
    await call.answer()


@router.callback_query(F.data.startswith("catalog:city:"))
async def show_products(call: CallbackQuery, session: AsyncSession) -> None:
    city_id = int(call.data.split(":")[2])
    city = await session.get(City, city_id)
    if city is None:
        await call.answer("Город не найден", show_alert=True)
        return
    res = await session.execute(
        select(Product)
        .where(Product.city_id == city_id, Product.is_active.is_(True))
        .order_by(Product.name)
    )
    products = list(res.scalars().all())
    title = texts.PRODUCTS_TITLE.format(city=city.name)
    if not products:
        await _safe_show(call, title + "\n\n" + texts.NO_PRODUCTS, kb.cities_kb(await _list_cities(session)))
    else:
        await _safe_show(call, title, kb.products_kb(products))
    await call.answer()


@router.callback_query(F.data.startswith("catalog:back_prod:"))
async def back_to_products(call: CallbackQuery, session: AsyncSession) -> None:
    product_id = int(call.data.split(":")[2])
    product = await session.get(Product, product_id)
    if product is None:
        await call.answer()
        return
    call.data = f"catalog:city:{product.city_id}"
    await show_products(call, session)


@router.callback_query(F.data.startswith("catalog:prod:"))
async def show_product(call: CallbackQuery, session: AsyncSession) -> None:
    product_id = int(call.data.split(":")[2])
    product = await session.get(Product, product_id)
    if product is None or not product.is_active:
        await call.answer("Товар недоступен", show_alert=True)
        return
    city = await session.get(City, product.city_id)
    text = texts.product_card(
        product.name,
        product.description,
        product.price_usdt,
        city.name if city else "—",
        product.stock,
    )
    markup = kb.product_card_kb(product.id)
    msg = call.message
    try:
        await msg.delete()
    except Exception:
        pass
    if product.photo_file_id:
        await msg.answer_photo(product.photo_file_id, caption=text, reply_markup=markup)
    else:
        await msg.answer(text, reply_markup=markup)
    await call.answer()
