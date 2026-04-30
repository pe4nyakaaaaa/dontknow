"""Тексты и шаблоны интерфейса."""

from __future__ import annotations

from decimal import Decimal

LINE = "━━━━━━━━━━━━━━━━━━━━━━"

WELCOME = (
    "✨ <b>Добро пожаловать в {name}!</b>\n"
    "{line}\n"
    "🏙 Выбирайте город и товар, складывайте в 🧺 корзину, "
    "оплачивайте с 💼 баланса или в крипте — а курьер всё привезёт лично.\n\n"
    "📦 История заказов, ⚖️ диспуты и 💬 отзывы — всё внутри бота.\n"
    "{line}"
)

MAIN_MENU = "🏠 <b>Главное меню</b>\n" + LINE + "\nВыберите действие 👇"

NO_CITIES = "🌆 Пока ни одного города не добавлено. Загляните чуть позже — мы расширяемся 🚀"
CITIES_TITLE = "🌆 <b>Выберите город</b>\n" + LINE
PRODUCTS_TITLE = "🛒 <b>Товары в городе:</b> {city}\n" + LINE
NO_PRODUCTS = "📭 В этом городе пока нет доступных товаров."

ORDER_HISTORY_TITLE = "📜 <b>История заказов</b>\n" + LINE
NO_ORDERS = "📭 У вас пока нет заказов."

REVIEWS_TITLE = "💬 <b>Отзывы покупателей</b>\n" + LINE
NO_REVIEWS = "🤍 Пока нет отзывов. Стань первым!"

CART_TITLE = "🧺 <b>Ваша корзина</b>\n" + LINE
CART_EMPTY = "🧺 Корзина пуста. Загляните в каталог 🛒"

WALLET_TITLE = "💼 <b>Кошелёк</b>\n" + LINE

ADMIN_PANEL = "🛠 <b>Админ-панель</b>\n" + LINE
COURIER_PANEL = "🚴 <b>Курьерский кабинет</b>\n" + LINE
MODERATOR_PANEL = "🛡 <b>Кабинет модератора</b>\n" + LINE


def format_money(value: Decimal | float | int) -> str:
    d = Decimal(str(value)).quantize(Decimal("0.01"))
    s = f"{d:.2f}"
    if s.endswith(".00"):
        s = s[:-3]
    return s


def product_card(name: str, description: str, price_usdt: Decimal | float, city: str, stock: int) -> str:
    if stock < 0:
        stock_line = "♾ в наличии"
    elif stock > 0:
        stock_line = f"🟢 в наличии: {stock}"
    else:
        stock_line = "🔴 нет в наличии"
    desc = description.strip() or "<i>Описание не указано</i>"
    return (
        f"🛍 <b>{name}</b>\n"
        f"{LINE}\n"
        f"🏙 Город: <b>{city}</b>\n"
        f"💰 Цена: <b>{format_money(price_usdt)} USDT</b>\n"
        f"{stock_line}\n\n"
        f"📝 {desc}"
    )


def order_summary(order_id: int, product_name: str, city: str, total: Decimal | float, status_label: str) -> str:
    return (
        f"🧾 <b>Заказ #{order_id}</b>\n"
        f"{LINE}\n"
        f"🛍 Товар: <b>{product_name}</b>\n"
        f"🏙 Город: {city}\n"
        f"💰 Сумма: <b>{format_money(total)} USDT</b>\n"
        f"📌 Статус: {status_label}"
    )


STATUS_LABELS = {
    "AWAITING_PAYMENT": "⏳ ждём оплату",
    "PAID": "✅ оплачено, ищем курьера",
    "IN_DELIVERY": "🚴 в доставке",
    "DELIVERED": "📦 доставлено",
    "CANCELED": "❌ отменён",
    "REFUNDED": "↩️ возврат",
    "DISPUTED": "⚖️ открыт диспут",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def wallet_card(balance: Decimal | float, free_credits: int) -> str:
    return (
        f"{WALLET_TITLE}\n"
        f"💰 Баланс: <b>{format_money(balance)} USDT</b>\n"
        f"🎁 Бесплатных заказов: <b>{free_credits}</b>"
    )


def topup_instructions(payment_id: int, amount: Decimal | float, method: str, wallet: str) -> str:
    return (
        f"💳 <b>Пополнение баланса #{payment_id}</b>\n"
        f"{LINE}\n"
        f"К оплате: <b>{format_money(amount)} USDT</b>\n"
        f"Способ: <b>{method}</b>\n\n"
        f"📥 Кошелёк для перевода:\n<code>{wallet}</code>\n\n"
        f"После перевода нажмите «✍️ Указать TX-хэш»."
    )


def cart_payment_instructions(payment_id: int, amount: Decimal | float, method: str, wallet: str) -> str:
    return (
        f"💳 <b>Оплата корзины #{payment_id}</b>\n"
        f"{LINE}\n"
        f"К оплате: <b>{format_money(amount)} USDT</b>\n"
        f"Способ: <b>{method}</b>\n\n"
        f"📥 Кошелёк для перевода:\n<code>{wallet}</code>\n\n"
        f"После перевода нажмите «✍️ Указать TX-хэш»."
    )


ASK_TXID = "✍️ Пришлите <b>TX-хэш</b> (ID транзакции) одним сообщением."

PAYMENT_RECEIVED = "🕒 Платёж принят на проверку. Мы уведомим вас, как только админ его подтвердит."

CHAT_OPENED = (
    "💬 <b>Чат по заказу #{order_id} открыт.</b>\n"
    "Все сообщения и фото будут переданы собеседнику.\n"
    "Чтобы выйти — нажмите «🚪 Выйти из чата»."
)

CHAT_CLOSED = "🚪 Вы вышли из чата."

NO_COURIER_FOR_CITY = "⚠️ В городе пока нет курьера. Админ назначит его и заказ автоматически передадут."

ORDER_ASSIGNED_COURIER = (
    "🚴 <b>Новый заказ #{order_id}</b>\n"
    "{line}\n"
    "🛍 Товар: <b>{product}</b>\n"
    "🏙 Город: <b>{city}</b>\n"
    "📍 Адрес: <code>{address}</code>"
)

DISPUTE_OPENED_BUYER = (
    "⚖️ <b>Диспут #{dispute_id} открыт</b> по заказу #{order_id}.\n"
    "Опишите проблему — мы передадим её модератору, после чего вы сможете общаться в чате."
)

DISPUTE_FOR_MODS = (
    "⚖️ <b>Новый диспут #{dispute_id}</b>\n"
    "{line}\n"
    "Заказ: #{order_id}\n"
    "Товар: <b>{product}</b>\n"
    "Покупатель: <a href=\"tg://user?id={buyer_id}\">{buyer_name}</a>\n\n"
    "Причина:\n<i>{reason}</i>\n\n"
    "Нажмите «🤝 Принять диспут», чтобы подключиться к чату."
)

DISPUTE_TAKEN_BUYER = "🛡 К диспуту #{dispute_id} подключился модератор. Можете общаться здесь."

DISPUTE_RESOLVED_REFUND = (
    "↩️ Модератор решил, что заказ #{order_id} нужно возместить.\n"
    "Вам начислен <b>1 бесплатный заказ</b> — выберите любой товар и при оформлении нажмите "
    "«🎁 Использовать бесплатный заказ»."
)

DISPUTE_RESOLVED_REJECT = "❌ Модератор отклонил диспут по заказу #{order_id}."
