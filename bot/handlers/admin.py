"""Админ-панель: города, товары, курьеры, бесплатные заказы, проверка платежей."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.models import (
    City,
    Order,
    OrderStatus,
    Payment,
    PaymentKind,
    PaymentStatus,
    Product,
    User,
    UserRole,
)
from bot.states import (
    AdminCitySG,
    AdminCourierSG,
    AdminFreeCreditsSG,
    AdminProductSG,
)
from bot.utils import display_name, is_admin

router = Router(name="admin")


def _admin_only(call: CallbackQuery) -> bool:
    if not is_admin(call.from_user.id):
        return False
    return True


# ---------- главное ----------


@router.callback_query(F.data == "admin:home")
async def admin_home(call: CallbackQuery, state: FSMContext) -> None:
    if not _admin_only(call):
        await call.answer("Доступ запрещён", show_alert=True)
        return
    await state.clear()
    await call.message.edit_text(texts.ADMIN_PANEL, reply_markup=kb.admin_home_kb())
    await call.answer()


# ---------- города ----------


@router.callback_query(F.data == "admin:cities")
async def admin_cities(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    res = await session.execute(select(City).order_by(City.name))
    cities = list(res.scalars().all())
    await call.message.edit_text("🌆 <b>Города</b>", reply_markup=kb.admin_cities_kb(cities))
    await call.answer()


@router.callback_query(F.data.startswith("admin:city:"))
async def admin_city_view(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    city = await session.get(City, city_id)
    if city is None:
        await call.answer("Город не найден", show_alert=True)
        return
    text = (
        f"🌆 <b>{city.name}</b>\n{texts.LINE}\n"
        f"Стоимость доставки: <b>{texts.format_money(city.delivery_price_usdt)} USDT</b>\n"
        f"Активен: {'🟢' if city.is_active else '🔴'}"
    )
    await call.message.edit_text(text, reply_markup=kb.admin_city_kb(city))
    await call.answer()


@router.callback_query(F.data.startswith("admin:city_toggle:"))
async def admin_city_toggle(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    city = await session.get(City, city_id)
    if city is None:
        await call.answer()
        return
    city.is_active = not city.is_active
    await session.flush()
    call.data = f"admin:city:{city_id}"
    await admin_city_view(call, session)


@router.callback_query(F.data.startswith("admin:city_del:"))
async def admin_city_delete(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    city = await session.get(City, city_id)
    if city is None:
        await call.answer()
        return
    await session.delete(city)
    await session.flush()
    await call.answer("Город удалён")
    call.data = "admin:cities"
    await admin_cities(call, session)


@router.callback_query(F.data == "admin:city_add")
async def admin_city_add(call: CallbackQuery, state: FSMContext) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    await state.set_state(AdminCitySG.waiting_name)
    await call.message.edit_text(
        "➕ Введите <b>название города</b>:",
        reply_markup=kb.back_button("admin:cities", "❌ Отмена"),
    )
    await call.answer()


@router.message(AdminCitySG.waiting_name, F.text)
async def admin_city_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 64:
        await message.answer("Название должно быть от 1 до 64 символов.")
        return
    await state.update_data(name=name)
    await state.set_state(AdminCitySG.waiting_delivery_price)
    await message.answer(
        f"Город: <b>{name}</b>\nВведите <b>стоимость доставки в USDT</b> (например <code>5</code> или <code>0</code>):"
    )


@router.message(AdminCitySG.waiting_delivery_price, F.text)
async def admin_city_price(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = Decimal(raw)
    except InvalidOperation:
        await message.answer("Введите число, например <code>5</code>.")
        return
    if price < 0:
        await message.answer("Цена не может быть отрицательной.")
        return

    data = await state.get_data()
    name = data.get("name", "")
    city = City(name=name, delivery_price_usdt=price, is_active=True)
    session.add(city)
    await session.flush()
    await state.clear()
    await message.answer(f"✅ Город <b>{name}</b> добавлен.", reply_markup=kb.back_button("admin:cities"))


# ---------- товары ----------


@router.callback_query(F.data == "admin:products")
async def admin_products_pick_city(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    res = await session.execute(select(City).order_by(City.name))
    cities = list(res.scalars().all())
    if not cities:
        await call.message.edit_text(
            "Сначала добавьте хотя бы один город.",
            reply_markup=kb.admin_home_kb(),
        )
    else:
        await call.message.edit_text(
            "🛍 <b>Товары</b>\nВыберите город:",
            reply_markup=kb.admin_products_pick_city_kb(cities),
        )
    await call.answer()


@router.callback_query(F.data.startswith("admin:prod_city:"))
async def admin_products_for_city(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    res = await session.execute(
        select(Product).where(Product.city_id == city_id).order_by(Product.name)
    )
    products = list(res.scalars().all())
    city = await session.get(City, city_id)
    title = f"🛍 <b>Товары города {city.name if city else city_id}</b>"
    await call.message.edit_text(title, reply_markup=kb.admin_products_kb(city_id, products))
    await call.answer()


@router.callback_query(F.data.startswith("admin:prod:"))
async def admin_product_view(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    prod_id = int(call.data.split(":")[2])
    product = await session.get(Product, prod_id)
    if product is None:
        await call.answer()
        return
    city = await session.get(City, product.city_id)
    text = (
        f"🛍 <b>{product.name}</b>\n{texts.LINE}\n"
        f"🏙 Город: {city.name if city else '—'}\n"
        f"💰 Цена: {texts.format_money(product.price_usdt)} USDT\n"
        f"📦 Остаток: {'∞' if product.stock < 0 else product.stock}\n"
        f"Активен: {'🟢' if product.is_active else '🔴'}\n\n"
        f"📝 {product.description or '—'}"
    )
    if product.photo_file_id:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer_photo(
            product.photo_file_id, caption=text, reply_markup=kb.admin_product_kb(product)
        )
    else:
        await call.message.edit_text(text, reply_markup=kb.admin_product_kb(product))
    await call.answer()


@router.callback_query(F.data.startswith("admin:prod_toggle:"))
async def admin_product_toggle(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    prod_id = int(call.data.split(":")[2])
    product = await session.get(Product, prod_id)
    if product is None:
        await call.answer()
        return
    product.is_active = not product.is_active
    await session.flush()
    call.data = f"admin:prod:{prod_id}"
    await admin_product_view(call, session)


@router.callback_query(F.data.startswith("admin:prod_del:"))
async def admin_product_delete(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    prod_id = int(call.data.split(":")[2])
    product = await session.get(Product, prod_id)
    if product is None:
        await call.answer()
        return
    city_id = product.city_id
    await session.delete(product)
    await session.flush()
    await call.answer("Товар удалён")
    call.data = f"admin:prod_city:{city_id}"
    await admin_products_for_city(call, session)


@router.callback_query(F.data.startswith("admin:prod_add:"))
async def admin_prod_add_start(call: CallbackQuery, state: FSMContext) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    await state.set_state(AdminProductSG.waiting_name)
    await state.update_data(city_id=city_id)
    await call.message.edit_text(
        "➕ <b>Новый товар</b>\nВведите <b>название</b>:",
        reply_markup=kb.back_button(f"admin:prod_city:{city_id}", "❌ Отмена"),
    )
    await call.answer()


@router.message(AdminProductSG.waiting_name, F.text)
async def prod_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 120:
        await message.answer("Название от 1 до 120 символов.")
        return
    await state.update_data(name=name)
    await state.set_state(AdminProductSG.waiting_description)
    await message.answer("Введите <b>описание</b> (или отправьте «-» если без описания):")


@router.message(AdminProductSG.waiting_description, F.text)
async def prod_desc(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip()
    if desc == "-":
        desc = ""
    await state.update_data(description=desc)
    await state.set_state(AdminProductSG.waiting_photo)
    await message.answer("Пришлите <b>фото</b> товара одним сообщением (или отправьте «-» чтобы пропустить):")


@router.message(AdminProductSG.waiting_photo, F.photo)
async def prod_photo(message: Message, state: FSMContext) -> None:
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_id)
    await state.set_state(AdminProductSG.waiting_price)
    await message.answer("Введите <b>цену в USDT</b> (например <code>10</code>):")


@router.message(AdminProductSG.waiting_photo, F.text)
async def prod_photo_skip(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() != "-":
        await message.answer("Пришлите фото или отправьте «-».")
        return
    await state.update_data(photo_file_id=None)
    await state.set_state(AdminProductSG.waiting_price)
    await message.answer("Введите <b>цену в USDT</b> (например <code>10</code>):")


@router.message(AdminProductSG.waiting_price, F.text)
async def prod_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = Decimal(raw)
    except InvalidOperation:
        await message.answer("Введите число.")
        return
    if price < 0:
        await message.answer("Цена не может быть отрицательной.")
        return
    await state.update_data(price=str(price))
    await state.set_state(AdminProductSG.waiting_stock)
    await message.answer(
        "Введите <b>остаток</b> (количество). Отправьте <code>-1</code> для безлимитного товара."
    )


@router.message(AdminProductSG.waiting_stock, F.text)
async def prod_stock(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    try:
        stock = int(raw)
    except ValueError:
        await message.answer("Введите целое число (например 10 или -1).")
        return

    data = await state.get_data()
    product = Product(
        city_id=int(data["city_id"]),
        name=data["name"],
        description=data.get("description") or "",
        photo_file_id=data.get("photo_file_id"),
        price_usdt=Decimal(str(data["price"])),
        stock=stock,
        is_active=True,
    )
    session.add(product)
    await session.flush()
    await state.clear()
    await message.answer(
        f"✅ Товар <b>{product.name}</b> добавлен.",
        reply_markup=kb.back_button(f"admin:prod_city:{product.city_id}"),
    )


# ---------- курьеры ----------


@router.callback_query(F.data == "admin:couriers")
async def admin_couriers(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    res = await session.execute(select(City).order_by(City.name))
    cities = list(res.scalars().all())
    if not cities:
        await call.message.edit_text("Сначала добавьте город.", reply_markup=kb.admin_home_kb())
    else:
        await call.message.edit_text(
            "🚴 <b>Курьеры</b>\nВыберите город:",
            reply_markup=kb.admin_couriers_kb(cities),
        )
    await call.answer()


@router.callback_query(F.data.startswith("admin:cour_city:"))
async def admin_courier_for_city(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    city = await session.get(City, city_id)
    res = await session.execute(select(User).where(User.courier_city_id == city_id))
    courier = res.scalars().first()
    text = f"🚴 <b>Курьер для {city.name if city else city_id}</b>\n{texts.LINE}\n"
    if courier:
        text += f"Сейчас: <a href=\"tg://user?id={courier.id}\">{display_name(courier)}</a> (id <code>{courier.id}</code>)"
    else:
        text += "Курьер не назначен."
    await call.message.edit_text(text, reply_markup=kb.admin_courier_city_kb(city_id, courier is not None))
    await call.answer()


@router.callback_query(F.data.startswith("admin:cour_set:"))
async def admin_courier_set_start(call: CallbackQuery, state: FSMContext) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    await state.set_state(AdminCourierSG.waiting_user_id)
    await state.update_data(city_id=city_id)
    await call.message.edit_text(
        "Введите <b>Telegram ID</b> пользователя, который станет курьером.\n"
        "Он должен сначала запустить бота через /start, чтобы появиться в базе.",
        reply_markup=kb.back_button(f"admin:cour_city:{city_id}", "❌ Отмена"),
    )
    await call.answer()


@router.message(AdminCourierSG.waiting_user_id, F.text)
async def admin_courier_set_apply(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    raw = (message.text or "").strip()
    try:
        target_id = int(raw)
    except ValueError:
        await message.answer("Введите числовой Telegram ID.")
        return

    data = await state.get_data()
    city_id = int(data["city_id"])
    target = await session.get(User, target_id)
    if target is None:
        await message.answer(
            "Пользователь не найден в БД. Попросите его запустить бота через /start и попробуйте снова."
        )
        return
    # снимем предыдущего курьера, если был
    res = await session.execute(select(User).where(User.courier_city_id == city_id))
    for old in res.scalars().all():
        old.courier_city_id = None
        old.role = UserRole.USER

    target.courier_city_id = city_id
    target.role = UserRole.COURIER
    await session.flush()
    await state.clear()

    city = await session.get(City, city_id)
    await message.answer(
        f"✅ {display_name(target)} назначен курьером города <b>{city.name if city else city_id}</b>.",
        reply_markup=kb.back_button(f"admin:cour_city:{city_id}"),
    )
    try:
        await message.bot.send_message(
            target.id,
            f"🚴 Вас назначили курьером города <b>{city.name if city else city_id}</b>.\n"
            f"Откройте 🏠 главное меню — появится «Кабинет курьера».",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin:cour_unset:"))
async def admin_courier_unset(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    city_id = int(call.data.split(":")[2])
    res = await session.execute(select(User).where(User.courier_city_id == city_id))
    found = list(res.scalars().all())
    for u in found:
        u.courier_city_id = None
        u.role = UserRole.USER
    await session.flush()
    await call.answer("Курьер снят")
    call.data = f"admin:cour_city:{city_id}"
    await admin_courier_for_city(call, session)


# ---------- бесплатные заказы ----------


@router.callback_query(F.data == "admin:credits")
async def admin_credits_start(call: CallbackQuery, state: FSMContext) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    await state.set_state(AdminFreeCreditsSG.waiting_user_id)
    await call.message.edit_text(
        "🎁 <b>Бесплатные заказы</b>\nВведите Telegram ID пользователя:",
        reply_markup=kb.back_button("admin:home", "❌ Отмена"),
    )
    await call.answer()


@router.message(AdminFreeCreditsSG.waiting_user_id, F.text)
async def admin_credits_user(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    try:
        target_id = int(raw)
    except ValueError:
        await message.answer("Введите числовой Telegram ID.")
        return
    target = await session.get(User, target_id)
    if target is None:
        await message.answer("Пользователь не найден.")
        return
    await state.update_data(target_id=target_id)
    await state.set_state(AdminFreeCreditsSG.waiting_amount)
    await message.answer(
        f"Текущее количество у {display_name(target)}: <b>{target.free_credits}</b>.\n"
        f"Введите изменение (положительное число — добавить, отрицательное — снять):"
    )


@router.message(AdminFreeCreditsSG.waiting_amount, F.text)
async def admin_credits_apply(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    try:
        delta = int((message.text or "").strip())
    except ValueError:
        await message.answer("Введите целое число.")
        return
    data = await state.get_data()
    target = await session.get(User, int(data["target_id"]))
    if target is None:
        await state.clear()
        await message.answer("Пользователь не найден.")
        return
    target.free_credits = max(0, target.free_credits + delta)
    await session.flush()
    await state.clear()
    await message.answer(
        f"✅ Готово. Теперь у {display_name(target)}: <b>{target.free_credits}</b>.",
        reply_markup=kb.back_button("admin:home"),
    )
    if delta > 0:
        try:
            await message.bot.send_message(
                target.id, f"🎁 Вам начислено бесплатных заказов: <b>{delta}</b>."
            )
        except Exception:
            pass


# ---------- проверка платежей ----------


@router.callback_query(F.data == "admin:payments")
async def admin_payments(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    res = await session.execute(
        select(Payment).where(Payment.status == PaymentStatus.PENDING_VERIFY).order_by(Payment.created_at)
    )
    payments = list(res.scalars().all())
    if not payments:
        await call.message.edit_text(
            "🧾 Нет платежей на проверке.", reply_markup=kb.admin_home_kb()
        )
    else:
        await call.message.edit_text(
            "🧾 <b>Платежи на проверке</b>", reply_markup=kb.admin_payments_kb(payments)
        )
    await call.answer()


@router.callback_query(F.data.startswith("admin:pay_view:"))
async def admin_payment_view(call: CallbackQuery, session: AsyncSession) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    pid = int(call.data.split(":")[2])
    payment = await session.get(Payment, pid)
    if payment is None:
        await call.answer("Платёж не найден", show_alert=True)
        return
    user = await session.get(User, payment.user_id)
    kind_label = "💼 Пополнение" if payment.kind == PaymentKind.TOPUP else "🧺 Оплата корзины"
    text = (
        f"{kind_label} #{payment.id}\n{texts.LINE}\n"
        f"Пользователь: <a href=\"tg://user?id={payment.user_id}\">{display_name(user)}</a>\n"
        f"Сумма: <b>{texts.format_money(payment.amount_usdt)} USDT</b>\n"
        f"Метод: {payment.method.value}\n"
        f"TX: <code>{payment.txid or '—'}</code>\n"
        f"Статус: {payment.status.value}"
    )
    if payment.kind == PaymentKind.ORDER_GROUP:
        res = await session.execute(select(Order).where(Order.payment_id == payment.id))
        orders = list(res.scalars().all())
        text += f"\n\nЗаказов: {len(orders)}"
    await call.message.edit_text(text, reply_markup=kb.admin_payment_view_kb(payment.id))
    await call.answer()


@router.callback_query(F.data.startswith("admin:pay_ok:"))
async def admin_payment_ok(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    pid = int(call.data.split(":")[2])
    payment = await session.get(Payment, pid)
    if payment is None or payment.status != PaymentStatus.PENDING_VERIFY:
        await call.answer("Платёж недоступен", show_alert=True)
        return

    payment.status = PaymentStatus.CONFIRMED
    payment.confirmed_at = datetime.now(UTC)

    if payment.kind == PaymentKind.TOPUP:
        user = await session.get(User, payment.user_id)
        if user is not None:
            user.balance_usdt = Decimal(str(user.balance_usdt)) + Decimal(str(payment.amount_usdt))
        await session.flush()
        try:
            await bot.send_message(
                payment.user_id,
                f"✅ Пополнение #{payment.id} подтверждено. На баланс зачислено "
                f"<b>{texts.format_money(payment.amount_usdt)} USDT</b>.",
                reply_markup=kb.back_to_main_kb(),
            )
        except Exception:
            pass
    else:
        # оплата корзины: переводим заказы в PAID и назначаем курьеров
        res = await session.execute(select(Order).where(Order.payment_id == payment.id))
        orders = list(res.scalars().all())
        for o in orders:
            if o.status == OrderStatus.AWAITING_PAYMENT:
                o.status = OrderStatus.PAID
                o.paid_at = datetime.now(UTC)
        await session.flush()

        from bot.handlers.delivery import assign_courier_and_notify
        try:
            await bot.send_message(
                payment.user_id,
                f"✅ Платёж #{payment.id} подтверждён. Заказов: <b>{len(orders)}</b>.\n"
                f"Курьер скоро свяжется с вами.",
                reply_markup=kb.back_to_main_kb(),
            )
        except Exception:
            pass
        for o in orders:
            await assign_courier_and_notify(bot, session, o)

    await call.message.edit_text(f"✅ Платёж #{payment.id} подтверждён.", reply_markup=kb.admin_home_kb())
    await call.answer("Подтверждено")


@router.callback_query(F.data.startswith("admin:pay_no:"))
async def admin_payment_no(call: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not _admin_only(call):
        await call.answer()
        return
    pid = int(call.data.split(":")[2])
    payment = await session.get(Payment, pid)
    if payment is None or payment.status != PaymentStatus.PENDING_VERIFY:
        await call.answer("Платёж недоступен", show_alert=True)
        return
    payment.status = PaymentStatus.REJECTED

    if payment.kind == PaymentKind.ORDER_GROUP:
        res = await session.execute(select(Order).where(Order.payment_id == payment.id))
        for o in res.scalars().all():
            if o.status == OrderStatus.AWAITING_PAYMENT:
                o.status = OrderStatus.CANCELED
                if o.stock_consumed:
                    product = await session.get(Product, o.product_id)
                    if product is not None and product.stock >= 0:
                        product.stock += 1
                    o.stock_consumed = False
        await session.flush()

    try:
        await bot.send_message(
            payment.user_id,
            f"❌ Платёж #{payment.id} отклонён администратором.\n"
            f"Если уверены, что перевод был — свяжитесь с поддержкой.",
            reply_markup=kb.back_to_main_kb(),
        )
    except Exception:
        pass

    await call.message.edit_text(f"❌ Платёж #{payment.id} отклонён.", reply_markup=kb.admin_home_kb())
    await call.answer("Отклонён")
