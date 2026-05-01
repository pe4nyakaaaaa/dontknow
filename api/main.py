"""FastAPI app entrypoint for the Mini App backend."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    admin,
    cart,
    catalog,
    courier,
    disputes,
    me,
    orders,
    reviews,
    wallet,
)
from bot.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    await init_db()
    yield


app = FastAPI(title="Telegram Sales Mini App API", lifespan=lifespan)

origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in origins_env.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


for r in (me.router, catalog.router, cart.router, wallet.router, orders.router,
          reviews.router, courier.router, disputes.router, admin.router):
    app.include_router(r, prefix="/api")
