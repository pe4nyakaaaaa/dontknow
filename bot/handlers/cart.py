"""Корзина и оформление заказа из корзины."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot import keyboards as kb
from bot import texts
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
from bot.states import CheckoutSG

router = Router(name="cart")


# ---------- helpers ----------


async def _load_cart(session: AsyncSession, user_id: int) -> list[CartItem]:
    res = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .options(selectinload(CartItem.product))
        .order_by(CartItem.added_at)
    )
    return list(res.scalars().all())


def _cart_total(items: list[CartItem], cities_by_id: dict[int, City]) -> tuple[Decimal, Decimal, Decimal]:
    """Возвращает (товары, доставка, итого) в USDT."""
    products_sum = Decimal("0")
    delivery_sum = Decimal("0")
    seen_cities: set[int] = set()
    for it in items:
        product_price = Decimal(str(it.product.price_usdt))
        products_sum += product_price * it.quantity
        if it.product.city_id not in seen_cities:
            seen_cities.add(it.product.city_id)
            city = cities_by_id.get(it.product.city_id)
            if city is not None:
                delivery_sum += Decimal(str(city.delivery_price_usdt))
    return products_sum, delivery_sum, products_sum + delivery_sum


def _format_cart_text(items: list[CartItem], cities_by_id: dict[int, City]) -> str:
    if not items:
        return texts.CART_TITLE + "\n\n" + texts.CART_EMPTY
    lines = [texts.CART_TITLE]
    for it in items:
        city = cities_by_id.get(it.product.city_id)
        line_total = Decimal(str(it.product.price_usdt)) * it.quantity
        lines.append(
            f"• <b>{it.product.name}</b> ×{it.quantity} — "
            f"<b>{texts.format_money(line_total)}</b> USDT "
            f"({city.name if city else '—'})"
        )
    products_sum, delivery_sum, total = _cart_total(items, cities_by_id)
    lines.append(texts.LINE)
    lines.append(f"🛍 Товары: <b>{texts.format_money(products_sum)}</b> USDT")
    lines.append(f"🚚 Доставка: <b>{texts.format_money(delivery_sum)}</b> USDT")
    lines.append(f"💰 Итого: <b>{texts.format_money(total)} USDT</b>")
    return "\n".join(lines)


async def _cities_map(session: AsyncSession, ids: list[int]) -> dict[int, City]:
    if not ids:
        return {}
    res = await session.execute(select(City).where(City.id.in_(ids)))
    return {c.id: c for c in res.scalars().all()}


async def _safe_show(call: CallbackQuery, text: str, markup) -> None:
    msg = call.message
    if msg.photo:
        try:
            await msg.delete()
        except Exception:
            pass
        await call.message.answer(text, reply_markup=markup)
    else:
        await msg.edit_text(text, reply_markup=markup)


# ---------- добавить / удалить / показать ----------


@router.callback_query(F.data.startswith("cart:add:"))
async def add_to_cart(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    product_id = int(call.data.split(":")[2])
    product = await session.get(Product, product_id)
    if product is None or not product.is_active:
        await call.answer("Товар недоступен", show_alert=True)
        return
    if product.stock == 0:
        await call.answer("Товара нет в наличии", show_alert=True)
        return

    res = await session.execute(
        select(CartItem).where(CartItem.user_id == db_user.id, CartItem.product_id == product.id)
    )
    item = res.scalars().first()
    if item is None:
        item = CartItem(user_id=db_user.id, product_id=product.id, quantity=1)
        session.add(item)
    else:
        item.quantity += 1
    await session.flush()
    await call.answer("✅ Добавлено в корзину")


@router.callback_query(F.data == "cart:show")
async def show_cart(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    items = await _load_cart(session, db_user.id)
    cities = await _cities_map(session, [it.product.city_id for it in items])
    text = _format_cart_text(items, cities)
    await _safe_show(call, text, kb.cart_kb(items, has_items=bool(items)))
    await call.answer()


@router.callback_query(F.data.startswith("cart:rm:"))
async def remove_from_cart(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    cart_item_id = int(call.data.split(":")[2])
    item = await session.get(CartItem, cart_item_id)
    if item is None or item.user_id != db_user.id:
        await call.answer()
        return
    await session.delete(item)
    await session.flush()
    await show_cart(call, session, db_user)


@router.callback_query(F.data == "cart:clear")
async def clear_cart(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    await session.execute(delete(CartItem).where(CartItem.user_id == db_user.id))
    await session.flush()
    await call.answer("Корзина очищена")
    await show_cart(call, session, db_user)


# ---------- оформление ----------


@router.callback_query(F.data == "cart:checkout")
async def start_checkout(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext
) -> None:
    items = await _load_cart(session, db_user.id)
    if not items:
        await call.answer("Корзина пуста", show_alert=True)
        return
    # уникальные города в порядке появления
    city_order: list[int] = []
    for it in items:
        if it.product.city_id not in city_order:
            city_order.append(it.product.city_id)

    await state.set_state(CheckoutSG.waiting_address)
    await state.update_data(pending_cities=city_order, addresses={})

    cities = await _cities_map(session, city_order)
    first_city = cities.get(city_order[0])
    city_name = first_city.name if first_city else "—"
    msg = call.message
    try:
        await msg.delete()
    except Exception:
        pass
    await msg.answer(
        f"📍 Введите <b>адрес доставки</b> для города <b>{city_name}</b>.\n"
        f"Укажите улицу, дом, квартиру, ориентир.",
        reply_markup=kb.back_button("cart:show", "❌ Отменить"),
    )
    await call.answer()


@router.message(CheckoutSG.waiting_address, F.text)
async def got_address(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    address = (message.text or "").strip()
    if len(address) < 5:
        await message.answer("Адрес слишком короткий. Пожалуйста, укажите подробнее.")
        return

    data = await state.get_data()
    pending: list[int] = list(data.get("pending_cities") or [])
    addresses: dict[int, str] = {int(k): v for k, v in (data.get("addresses") or {}).items()}
    if not pending:
        await state.clear()
        await message.answer("Что-то пошло не так. Попробуйте ещё раз с корзины.",
                             reply_markup=kb.back_to_main_kb())
        return

    city_id = pending.pop(0)
    addresses[city_id] = address

    if pending:
        cities = await _cities_map(session, pending[:1])
        next_city = cities.get(pending[0])
        await state.update_data(pending_cities=pending, addresses=addresses)
        await message.answer(
            f"📍 Теперь адрес для города <b>{next_city.name if next_city else '—'}</b>:",
            reply_markup=kb.back_button("cart:show", "❌ Отменить"),
        )
        return

    # все адреса собраны → показываем выбор оплаты
    await state.update_data(pending_cities=[], addresses=addresses)
    await state.set_state(CheckoutSG.waiting_method)

    items = await _load_cart(session, db_user.id)
    cities = await _cities_map(session, [it.product.city_id for it in items])
    _, _, total = _cart_total(items, cities)

    can_pay_with_balance = Decimal(str(db_user.balance_usdt)) >= total
    free_credits = db_user.free_credits if len(items) == 1 and items[0].quantity == 1 else 0

    summary = _format_cart_text(items, cities)
    summary += f"\n\n💼 Баланс: <b>{texts.format_money(db_user.balance_usdt)}</b> USDT"
    if can_pay_with_balance:
        summary += "\n✅ Хватает на оплату с баланса."
    else:
        need = total - Decimal(str(db_user.balance_usdt))
        summary += f"\n⚠️ Не хватает на балансе: <b>{texts.format_money(need)}</b> USDT."
    summary += "\n\nВыберите способ оплаты 👇"

    await message.answer(
        summary,
        reply_markup=kb.checkout_methods_kb(
            can_pay_with_balance=can_pay_with_balance, free_credits=free_credits
        ),
    )


@router.callback_query(CheckoutSG.waiting_method, F.data.startswith("checkout:pay:"))
async def pick_checkout_method(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext
) -> None:
    method = call.data.split(":")[2]
    items = await _load_cart(session, db_user.id)
    if not items:
        await state.clear()
        await call.answer("Корзина пуста", show_alert=True)
        return

    data = await state.get_data()
    addresses: dict[int, str] = {int(k): v for k, v in (data.get("addresses") or {}).items()}
    cities = await _cities_map(session, [it.product.city_id for it in items])
    products_sum, delivery_sum, total = _cart_total(items, cities)

    if method == "BALANCE":
        if Decimal(str(db_user.balance_usdt)) < total:
            await call.answer("На балансе недостаточно", show_alert=True)
            return
        # списываем с баланса, создаём заказы как PAID
        db_user.balance_usdt = Decimal(str(db_user.balance_usdt)) - total
        orders = await _create_orders_from_cart(
            session, db_user, items, cities, addresses, paid=True, method=PaymentMethod.BALANCE
        )
        await _flush_cart(session, db_user.id)
        await state.clear()
        await call.message.edit_text(
            f"✅ Оплата с баланса прошла. Создано заказов: <b>{len(orders)}</b>.\n"
            f"Списано: <b>{texts.format_money(total)} USDT</b>.\n"
            f"Скоро курьер свяжется с вами.",
            reply_markup=kb.back_to_main_kb(),
        )
        from bot.handlers.delivery import assign_courier_and_notify
        for o in orders:
            await assign_courier_and_notify(call.bot, session, o)
        await call.answer()
        return

    if method == "FREE_CREDIT":
        if db_user.free_credits <= 0 or len(items) != 1 or items[0].quantity != 1:
            await call.answer("Бесплатный заказ нельзя применить", show_alert=True)
            return
        db_user.free_credits -= 1
        orders = await _create_orders_from_cart(
            session, db_user, items, cities, addresses, paid=True,
            method=PaymentMethod.FREE_CREDIT, free=True,
        )
        await _flush_cart(session, db_user.id)
        await state.clear()
        await call.message.edit_text(
            f"🎁 Бесплатный заказ оформлен! Заказ #{orders[0].id}.\n"
            f"Курьер скоро свяжется с вами.",
            reply_markup=kb.back_to_main_kb(),
        )
        from bot.handlers.delivery import assign_courier_and_notify
        for o in orders:
            await assign_courier_and_notify(call.bot, session, o)
        await call.answer()
        return

    if method not in ("TON", "USDT_TRC20"):
        await call.answer()
        return

    # внешняя оплата: создаём Payment + Orders в AWAITING_PAYMENT
    payment = Payment(
        user_id=db_user.id,
        kind=PaymentKind.ORDER_GROUP,
        amount_usdt=total,
        method=PaymentMethod(method),
        status=PaymentStatus.PENDING_PAYMENT,
    )
    session.add(payment)
    await session.flush()

    orders = await _create_orders_from_cart(
        session, db_user, items, cities, addresses, paid=False,
        method=PaymentMethod(method), payment_id=payment.id,
    )
    await _flush_cart(session, db_user.id)

    wallet = settings.ton_wallet if method == "TON" else settings.usdt_trc20_wallet
    method_label = "TON" if method == "TON" else "USDT (TRC-20)"
    await state.update_data(payment_id=payment.id)

    await call.message.edit_text(
        texts.cart_payment_instructions(payment.id, total, method_label, wallet or "—"),
        reply_markup=kb.confirm_external_payment_kb(payment.id),
    )
    await call.answer()


async def _flush_cart(session: AsyncSession, user_id: int) -> None:
    await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
    await session.flush()


async def _create_orders_from_cart(
    session: AsyncSession,
    db_user: User,
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
    for it in items:
        product = it.product
        city = cities.get(product.city_id)
        for _ in range(it.quantity):
            unit_product = Decimal("0") if free else Decimal(str(product.price_usdt))
            unit_delivery = Decimal("0")  # доставка считалась один раз на город — добавим к первому заказу города
            order = Order(
                user_id=db_user.id,
                product_id=product.id,
                city_id=product.city_id,
                delivery_address=addresses.get(product.city_id),
                product_price_usdt=unit_product,
                delivery_price_usdt=unit_delivery,
                total_usdt=unit_product + unit_delivery,
                status=OrderStatus.PAID if paid else OrderStatus.AWAITING_PAYMENT,
                payment_method=method,
                payment_id=payment_id,
                is_free=free,
            )
            if paid:
                order.paid_at = datetime.now(UTC)
            if product.stock > 0:
                product.stock -= 1
            session.add(order)
            orders.append(order)

        # доставка — первому заказу города
        if not free and city is not None:
            delivery_amount = Decimal(str(city.delivery_price_usdt))
            if delivery_amount > 0:
                first_for_city = next(
                    (o for o in orders if o.city_id == city.id and o.delivery_price_usdt == 0),
                    None,
                )
                if first_for_city is not None:
                    first_for_city.delivery_price_usdt = delivery_amount
                    first_for_city.total_usdt = (
                        Decimal(str(first_for_city.product_price_usdt)) + delivery_amount
                    )
    await session.flush()
    return orders


@router.callback_query(F.data.startswith("checkout:txid:"))
async def request_txid(call: CallbackQuery, state: FSMContext) -> None:
    payment_id = int(call.data.split(":")[2])
    await state.set_state(CheckoutSG.waiting_txid)
    await state.update_data(payment_id=payment_id)
    await call.message.answer(texts.ASK_TXID)
    await call.answer()


@router.message(CheckoutSG.waiting_txid, F.text)
async def got_txid(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, bot: Bot
) -> None:
    data = await state.get_data()
    payment_id = int(data.get("payment_id", 0))
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.user_id != db_user.id:
        await state.clear()
        await message.answer("Платёж не найден.", reply_markup=kb.back_to_main_kb())
        return
    if payment.status != PaymentStatus.PENDING_PAYMENT:
        await state.clear()
        await message.answer("Этот платёж уже не ждёт TX.", reply_markup=kb.back_to_main_kb())
        return

    txid = (message.text or "").strip()
    if len(txid) < 4:
        await message.answer("TX-хэш слишком короткий. Попробуйте ещё раз.")
        return

    payment.txid = txid
    payment.status = PaymentStatus.PENDING_VERIFY
    await session.flush()
    await state.clear()

    await message.answer(texts.PAYMENT_RECEIVED, reply_markup=kb.back_to_main_kb())

    notify = (
        f"🧾 <b>Новый платёж по корзине #{payment.id}</b>\n"
        f"От: <a href=\"tg://user?id={db_user.id}\">{db_user.full_name or db_user.id}</a>\n"
        f"Сумма: <b>{texts.format_money(payment.amount_usdt)} USDT</b>\n"
        f"Метод: {payment.method.value}\n"
        f"TX: <code>{txid}</code>"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, notify, reply_markup=kb.admin_payment_view_kb(payment.id))
        except Exception:
            pass


@router.callback_query(F.data.startswith("checkout:cancel:"))
async def cancel_checkout(
    call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext
) -> None:
    payment_id = int(call.data.split(":")[2])
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.user_id != db_user.id:
        await call.answer()
        return
    if payment.status not in (PaymentStatus.PENDING_PAYMENT, PaymentStatus.PENDING_VERIFY):
        await call.answer("Нельзя отменить", show_alert=True)
        return
    payment.status = PaymentStatus.REJECTED
    # отменяем привязанные заказы
    res = await session.execute(select(Order).where(Order.payment_id == payment.id))
    for o in res.scalars().all():
        if o.status == OrderStatus.AWAITING_PAYMENT:
            o.status = OrderStatus.CANCELED
    await session.flush()
    await state.clear()
    await call.message.edit_text("❌ Оформление отменено.", reply_markup=kb.back_to_main_kb())
    await call.answer()
