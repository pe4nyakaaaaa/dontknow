"""Pydantic schemas for API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CityOut(_CamelModel):
    id: int
    name: str
    delivery_price_usdt: float
    is_active: bool
    products_count: int = 0


class ProductOut(_CamelModel):
    id: int
    city_id: int
    city_name: str
    name: str
    description: str
    photo_url: str | None = None
    price_usdt: float
    stock: int
    is_active: bool


class CartItemOut(_CamelModel):
    id: int
    product_id: int
    product_name: str
    city_id: int
    city_name: str
    price_usdt: float
    delivery_price_usdt: float
    quantity: int
    photo_url: str | None = None


class CartOut(BaseModel):
    items: list[CartItemOut]
    items_total_usdt: float
    delivery_total_usdt: float
    total_usdt: float


class CartAddIn(BaseModel):
    product_id: int
    quantity: int = 1


class CartUpdateIn(BaseModel):
    quantity: int


class WalletOut(BaseModel):
    balance_usdt: float
    free_credits: int


class TopupCreateIn(BaseModel):
    amount_usdt: float
    method: str  # TON | USDT_TRC20


class TopupSubmitTxIn(BaseModel):
    txid: str


class PaymentOut(_CamelModel):
    id: int
    kind: str
    amount_usdt: float
    method: str
    status: str
    txid: str | None = None
    created_at: datetime
    confirmed_at: datetime | None = None


class CheckoutAddressIn(BaseModel):
    city_id: int
    address: str


class CheckoutIn(BaseModel):
    method: str  # BALANCE | TON | USDT_TRC20
    addresses: list[CheckoutAddressIn]


class CheckoutOut(BaseModel):
    paid_from_balance: bool
    payment_id: int | None = None
    order_ids: list[int]
    crypto_wallet: str | None = None
    amount_usdt: float | None = None
    method: str


class OrderListItem(_CamelModel):
    id: int
    status: str
    product_name: str
    city_name: str
    total_usdt: float
    created_at: datetime


class OrderDetailOut(_CamelModel):
    id: int
    status: str
    product_id: int
    product_name: str
    city_id: int
    city_name: str
    delivery_address: str | None
    payment_method: str | None
    product_price_usdt: float
    delivery_price_usdt: float
    total_usdt: float
    is_free: bool
    courier_id: int | None
    courier_name: str | None
    created_at: datetime
    paid_at: datetime | None
    delivered_at: datetime | None


class ChatMessageOut(_CamelModel):
    id: int
    sender_id: int
    sender_name: str
    kind: str
    text: str | None
    photo_url: str | None = None
    created_at: datetime


class ChatSendIn(BaseModel):
    text: str | None = None
    photo_data_url: str | None = None  # base64 inline image (data:image/...;base64,...)


class ReviewOut(_CamelModel):
    id: int
    user_name: str
    rating: int
    text: str
    created_at: datetime


class ReviewCreateIn(BaseModel):
    order_id: int
    rating: int
    text: str = ""


class DisputeOpenIn(BaseModel):
    order_id: int
    reason: str


class DisputeOut(_CamelModel):
    id: int
    order_id: int
    status: str
    reason: str
    moderator_id: int | None
    moderator_name: str | None
    opened_at: datetime
    closed_at: datetime | None


class DisputeResolveIn(BaseModel):
    refund: bool
    note: str = ""


class MeOut(BaseModel):
    id: int
    username: str | None
    full_name: str | None
    balance_usdt: float
    free_credits: int
    is_admin: bool
    is_moderator: bool
    courier_city_id: int | None


# Admin

class CityCreateIn(BaseModel):
    name: str
    delivery_price_usdt: float = 0


class CityUpdateIn(BaseModel):
    name: str | None = None
    delivery_price_usdt: float | None = None
    is_active: bool | None = None


class ProductCreateIn(BaseModel):
    city_id: int
    name: str
    description: str = ""
    price_usdt: float
    stock: int = -1
    photo_url: str | None = None


class ProductUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    price_usdt: float | None = None
    stock: int | None = None
    is_active: bool | None = None
    photo_url: str | None = None


class CourierAssignIn(BaseModel):
    user_id: int
    city_id: int


class FreeCreditsIn(BaseModel):
    user_id: int
    amount: int = 1


class PaymentDecisionIn(BaseModel):
    note: str = ""
