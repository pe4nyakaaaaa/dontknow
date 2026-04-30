"""Кошелёк: баланс, пополнение, история платежей."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import keyboards as kb
from bot import texts
from bot.config import settings
from bot.models import Payment, PaymentKind, PaymentMethod, PaymentStatus, User
from bot.states import TopupSG

router = Router(name="balance")


@router.callback_query(F.data == "wallet:show")
async def show_wallet(call: CallbackQuery, db_user: User, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        texts.wallet_card(db_user.balance_usdt, db_user.free_credits),
        reply_markup=kb.wallet_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "wallet:history")
async def show_history(call: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    res = await session.execute(
        select(Payment).where(Payment.user_id == db_user.id).order_by(Payment.created_at.desc()).limit(20)
    )
    payments = list(res.scalars().all())
    if not payments:
        text = texts.WALLET_TITLE + "\n\n📭 История пуста."
    else:
        lines = [texts.WALLET_TITLE]
        for p in payments:
            kind_emoji = "💼" if p.kind == PaymentKind.TOPUP else "🧺"
            status_label = {
                PaymentStatus.PENDING_PAYMENT: "⏳ ждём TX",
                PaymentStatus.PENDING_VERIFY: "🔎 проверка",
                PaymentStatus.CONFIRMED: "✅ подтверждён",
                PaymentStatus.REJECTED: "❌ отклонён",
            }[p.status]
            lines.append(
                f"{kind_emoji} #{p.id} • <b>{texts.format_money(p.amount_usdt)} USDT</b> "
                f"• {p.method.value} • {status_label}"
            )
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=kb.wallet_kb())
    await call.answer()


@router.callback_query(F.data == "wallet:topup")
async def start_topup(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TopupSG.waiting_amount)
    await call.message.edit_text(
        "💳 <b>Пополнение баланса</b>\n" + texts.LINE +
        "\nВведите сумму в <b>USDT</b> (например: <code>25</code> или <code>50.5</code>):",
        reply_markup=kb.back_button("wallet:show", "❌ Отмена"),
    )
    await call.answer()


@router.message(TopupSG.waiting_amount, F.text)
async def got_topup_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await message.answer("Введите число, например <code>25</code> или <code>50.5</code>.")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть положительной.")
        return
    if amount > Decimal("100000"):
        await message.answer("Слишком большая сумма.")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(TopupSG.waiting_method)
    await message.answer(
        f"Сумма пополнения: <b>{texts.format_money(amount)} USDT</b>\n"
        f"Выберите способ оплаты:",
        reply_markup=kb.topup_methods_kb(),
    )


@router.callback_query(TopupSG.waiting_method, F.data.startswith("topup:method:"))
async def topup_pick_method(
    call: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    method_s = call.data.split(":")[2]
    if method_s not in ("TON", "USDT_TRC20"):
        await call.answer()
        return
    data = await state.get_data()
    amount = Decimal(str(data.get("amount", "0")))
    method = PaymentMethod(method_s)

    payment = Payment(
        user_id=db_user.id,
        kind=PaymentKind.TOPUP,
        amount_usdt=amount,
        method=method,
        status=PaymentStatus.PENDING_PAYMENT,
    )
    session.add(payment)
    await session.flush()

    wallet = settings.ton_wallet if method == PaymentMethod.TON else settings.usdt_trc20_wallet
    method_label = "TON" if method == PaymentMethod.TON else "USDT (TRC-20)"
    await state.update_data(payment_id=payment.id)

    await call.message.edit_text(
        texts.topup_instructions(payment.id, amount, method_label, wallet or "—"),
        reply_markup=kb.topup_confirm_kb(payment.id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("topup:txid:"))
async def topup_request_txid(call: CallbackQuery, state: FSMContext) -> None:
    payment_id = int(call.data.split(":")[2])
    await state.set_state(TopupSG.waiting_txid)
    await state.update_data(payment_id=payment_id)
    await call.message.answer(texts.ASK_TXID)
    await call.answer()


@router.message(TopupSG.waiting_txid, F.text)
async def topup_got_txid(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User, bot: Bot
) -> None:
    data = await state.get_data()
    payment_id = int(data.get("payment_id", 0))
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.user_id != db_user.id or payment.kind != PaymentKind.TOPUP:
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
        f"💼 <b>Новое пополнение баланса #{payment.id}</b>\n"
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


@router.callback_query(F.data.startswith("topup:cancel:"))
async def topup_cancel(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext) -> None:
    payment_id = int(call.data.split(":")[2])
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.user_id != db_user.id:
        await call.answer()
        return
    if payment.status not in (PaymentStatus.PENDING_PAYMENT, PaymentStatus.PENDING_VERIFY):
        await call.answer("Нельзя отменить", show_alert=True)
        return
    payment.status = PaymentStatus.REJECTED
    await session.flush()
    await state.clear()
    await call.message.edit_text("❌ Пополнение отменено.", reply_markup=kb.back_to_main_kb())
    await call.answer()
