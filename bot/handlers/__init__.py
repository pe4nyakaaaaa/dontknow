from aiogram import Router

from bot.handlers import (
    admin,
    balance,
    cart,
    catalog,
    common,
    delivery,
    disputes,
    orders,
    reviews,
)


def build_router() -> Router:
    """Главный роутер. Сначала включаем чат-режимы (delivery/disputes), чтобы
    их FSM-фильтры перехватили текст/фото внутри активного чата раньше остальных."""
    router = Router()
    router.include_router(common.router)
    router.include_router(delivery.router)
    router.include_router(disputes.router)
    router.include_router(catalog.router)
    router.include_router(cart.router)
    router.include_router(balance.router)
    router.include_router(orders.router)
    router.include_router(reviews.router)
    router.include_router(admin.router)
    return router
