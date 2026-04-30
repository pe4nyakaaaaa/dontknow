"""Inline-клавиатуры."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.models import CartItem, City, Order, Product

# ----- основное меню -----

def main_menu(*, is_admin: bool, is_courier: bool, is_moderator: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Каталог", callback_data="catalog:cities")
    kb.button(text="🧺 Корзина", callback_data="cart:show")
    kb.button(text="💼 Кошелёк", callback_data="wallet:show")
    kb.button(text="📜 Мои заказы", callback_data="orders:list")
    kb.button(text="💬 Отзывы", callback_data="reviews:list")
    kb.button(text="✍️ Оставить отзыв", callback_data="reviews:new")
    if is_courier:
        kb.button(text="🚴 Кабинет курьера", callback_data="courier:home")
    if is_moderator:
        kb.button(text="🛡 Кабинет модератора", callback_data="mod:home")
    if is_admin:
        kb.button(text="🛠 Админ-панель", callback_data="admin:home")
    kb.adjust(2, 2, 2, 1, 1, 1)
    return kb.as_markup()


def back_button(callback: str = "main", text: str = "⬅️ Назад") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=callback)
    return kb.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню", callback_data="main")
    return kb.as_markup()


# ----- каталог -----

def cities_kb(cities: list[City]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for city in cities:
        kb.button(text=f"🏙 {city.name}", callback_data=f"catalog:city:{city.id}")
    kb.button(text="⬅️ Главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def products_kb(products: list[Product]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=f"🛍 {p.name}", callback_data=f"catalog:prod:{p.id}")
    kb.button(text="⬅️ Города", callback_data="catalog:cities")
    kb.adjust(1)
    return kb.as_markup()


def product_card_kb(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🧺 В корзину", callback_data=f"cart:add:{product_id}")
    kb.button(text="⬅️ К списку", callback_data=f"catalog:back_prod:{product_id}")
    kb.adjust(1)
    return kb.as_markup()


# ----- корзина -----

def cart_kb(items: list[CartItem], *, has_items: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for it in items:
        kb.button(text=f"🗑 {it.product.name} ×{it.quantity}", callback_data=f"cart:rm:{it.id}")
    if has_items:
        kb.button(text="✅ Оформить заказ", callback_data="cart:checkout")
        kb.button(text="🧹 Очистить", callback_data="cart:clear")
    kb.button(text="⬅️ Главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def checkout_methods_kb(*, can_pay_with_balance: bool, free_credits: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if can_pay_with_balance:
        kb.button(text="💼 Оплатить с баланса", callback_data="checkout:pay:BALANCE")
    if free_credits > 0:
        kb.button(text=f"🎁 Использовать бесплатный заказ ({free_credits})",
                  callback_data="checkout:pay:FREE_CREDIT")
    kb.button(text="💎 TON", callback_data="checkout:pay:TON")
    kb.button(text="💵 USDT (TRC-20)", callback_data="checkout:pay:USDT_TRC20")
    kb.button(text="❌ Отменить", callback_data="cart:show")
    kb.adjust(1)
    return kb.as_markup()


def confirm_external_payment_kb(payment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Указать TX-хэш", callback_data=f"checkout:txid:{payment_id}")
    kb.button(text="❌ Отменить", callback_data=f"checkout:cancel:{payment_id}")
    kb.adjust(1)
    return kb.as_markup()


# ----- кошелёк / пополнение -----

def wallet_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Пополнить", callback_data="wallet:topup")
    kb.button(text="📜 История платежей", callback_data="wallet:history")
    kb.button(text="⬅️ Главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def topup_methods_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 TON", callback_data="topup:method:TON")
    kb.button(text="💵 USDT (TRC-20)", callback_data="topup:method:USDT_TRC20")
    kb.button(text="❌ Отменить", callback_data="wallet:show")
    kb.adjust(2, 1)
    return kb.as_markup()


def topup_confirm_kb(payment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Указать TX-хэш", callback_data=f"topup:txid:{payment_id}")
    kb.button(text="❌ Отменить", callback_data=f"topup:cancel:{payment_id}")
    kb.adjust(1)
    return kb.as_markup()


# ----- мои заказы -----

def orders_list_kb(orders: list[Order]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"#{o.id} • {o.status.value}", callback_data=f"orders:view:{o.id}")
    kb.button(text="⬅️ Главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def order_view_kb(order: Order, *, is_courier_view: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    status = order.status.value
    if is_courier_view:
        if status == "PAID":
            kb.button(text="✅ Принять заказ", callback_data=f"courier:take:{order.id}")
        if status == "IN_DELIVERY":
            kb.button(text="💬 Чат с покупателем", callback_data=f"chat:open:{order.id}")
            kb.button(text="📦 Доставлено", callback_data=f"courier:deliver:{order.id}")
        kb.button(text="⬅️ Кабинет курьера", callback_data="courier:home")
    else:
        if status == "IN_DELIVERY":
            kb.button(text="💬 Чат с курьером", callback_data=f"chat:open:{order.id}")
        if status in ("PAID", "IN_DELIVERY", "DELIVERED"):
            kb.button(text="⚖️ Открыть диспут", callback_data=f"dispute:open:{order.id}")
        if status == "DELIVERED":
            kb.button(text="✍️ Оставить отзыв", callback_data=f"reviews:for:{order.id}")
        kb.button(text="⬅️ К заказам", callback_data="orders:list")
    kb.adjust(1)
    return kb.as_markup()


def in_chat_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚪 Выйти из чата", callback_data="chat:exit")
    return kb.as_markup()


def in_dispute_chat_kb(dispute_id: int, *, is_moderator: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚪 Выйти из чата", callback_data="dispute:exit")
    if is_moderator:
        kb.button(text="↩️ Возместить (бесплатный заказ)", callback_data=f"dispute:resolve_refund:{dispute_id}")
        kb.button(text="❌ Отклонить", callback_data=f"dispute:resolve_reject:{dispute_id}")
    kb.adjust(1)
    return kb.as_markup()


# ----- отзывы -----

def rating_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"review:rate:{i}")
    kb.button(text="❌ Отмена", callback_data="main")
    kb.adjust(5, 1)
    return kb.as_markup()


def review_skip_text_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Без текста", callback_data="review:skip_text")
    kb.button(text="❌ Отмена", callback_data="main")
    return kb.as_markup()


# ----- админ -----

def admin_home_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌆 Города", callback_data="admin:cities")
    kb.button(text="🛍 Товары", callback_data="admin:products")
    kb.button(text="🚴 Курьеры", callback_data="admin:couriers")
    kb.button(text="🎁 Бесплатные заказы", callback_data="admin:credits")
    kb.button(text="🧾 Платежи на проверке", callback_data="admin:payments")
    kb.button(text="⬅️ Главное меню", callback_data="main")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def admin_cities_kb(cities: list[City]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for city in cities:
        mark = "🟢" if city.is_active else "🔴"
        kb.button(text=f"{mark} {city.name}", callback_data=f"admin:city:{city.id}")
    kb.button(text="➕ Добавить город", callback_data="admin:city_add")
    kb.button(text="⬅️ Назад", callback_data="admin:home")
    kb.adjust(1)
    return kb.as_markup()


def admin_city_kb(city: City) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "🔴 Деактивировать" if city.is_active else "🟢 Активировать"
    kb.button(text=toggle, callback_data=f"admin:city_toggle:{city.id}")
    kb.button(text="🗑 Удалить", callback_data=f"admin:city_del:{city.id}")
    kb.button(text="⬅️ К городам", callback_data="admin:cities")
    kb.adjust(1)
    return kb.as_markup()


def admin_products_pick_city_kb(cities: list[City]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for city in cities:
        kb.button(text=f"🏙 {city.name}", callback_data=f"admin:prod_city:{city.id}")
    kb.button(text="⬅️ Назад", callback_data="admin:home")
    kb.adjust(1)
    return kb.as_markup()


def admin_products_kb(city_id: int, products: list[Product]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        mark = "🟢" if p.is_active else "🔴"
        kb.button(text=f"{mark} {p.name}", callback_data=f"admin:prod:{p.id}")
    kb.button(text="➕ Добавить товар", callback_data=f"admin:prod_add:{city_id}")
    kb.button(text="⬅️ К городам", callback_data="admin:products")
    kb.adjust(1)
    return kb.as_markup()


def admin_product_kb(product: Product) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "🔴 Скрыть" if product.is_active else "🟢 Показать"
    kb.button(text=toggle, callback_data=f"admin:prod_toggle:{product.id}")
    kb.button(text="🗑 Удалить", callback_data=f"admin:prod_del:{product.id}")
    kb.button(text="⬅️ К товарам", callback_data=f"admin:prod_city:{product.city_id}")
    kb.adjust(1)
    return kb.as_markup()


def admin_couriers_kb(cities: list[City]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for city in cities:
        kb.button(text=f"🏙 {city.name}", callback_data=f"admin:cour_city:{city.id}")
    kb.button(text="⬅️ Назад", callback_data="admin:home")
    kb.adjust(1)
    return kb.as_markup()


def admin_courier_city_kb(city_id: int, has_courier: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Назначить курьера", callback_data=f"admin:cour_set:{city_id}")
    if has_courier:
        kb.button(text="🗑 Снять курьера", callback_data=f"admin:cour_unset:{city_id}")
    kb.button(text="⬅️ К городам", callback_data="admin:couriers")
    kb.adjust(1)
    return kb.as_markup()


def admin_payments_kb(payments: list) -> InlineKeyboardMarkup:
    """payments: list of Payment ORM."""
    kb = InlineKeyboardBuilder()
    for p in payments:
        label_kind = "💼" if p.kind.value == "TOPUP" else "🧺"
        kb.button(
            text=f"{label_kind} #{p.id} • {p.amount_usdt} USDT",
            callback_data=f"admin:pay_view:{p.id}",
        )
    kb.button(text="⬅️ Назад", callback_data="admin:home")
    kb.adjust(1)
    return kb.as_markup()


def admin_payment_view_kb(payment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"admin:pay_ok:{payment_id}")
    kb.button(text="❌ Отклонить", callback_data=f"admin:pay_no:{payment_id}")
    kb.button(text="⬅️ Назад", callback_data="admin:payments")
    kb.adjust(1)
    return kb.as_markup()


# ----- курьер / модератор -----

def courier_home_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Активные заказы", callback_data="courier:active")
    kb.button(text="📜 История", callback_data="courier:history")
    kb.button(text="⬅️ Главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def moderator_home_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚖️ Открытые диспуты", callback_data="mod:open")
    kb.button(text="⬅️ Главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def disputes_list_kb(items: list[tuple[int, int]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for dispute_id, order_id in items:
        kb.button(text=f"⚖️ #{dispute_id} • заказ #{order_id}",
                  callback_data=f"mod:dispute:{dispute_id}")
    kb.button(text="⬅️ Назад", callback_data="mod:home")
    kb.adjust(1)
    return kb.as_markup()


def dispute_take_kb(dispute_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🤝 Принять диспут", callback_data=f"mod:take:{dispute_id}")
    kb.button(text="⬅️ Назад", callback_data="mod:open")
    kb.adjust(1)
    return kb.as_markup()
