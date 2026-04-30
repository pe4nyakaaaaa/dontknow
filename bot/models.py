"""Модели SQLAlchemy."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(StrEnum):
    USER = "USER"
    COURIER = "COURIER"


class OrderStatus(StrEnum):
    AWAITING_PAYMENT = "AWAITING_PAYMENT"      # включён в оплачиваемую группу, ждём подтверждения
    PAID = "PAID"
    IN_DELIVERY = "IN_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"


class PaymentMethod(StrEnum):
    TON = "TON"
    USDT_TRC20 = "USDT_TRC20"
    BALANCE = "BALANCE"
    FREE_CREDIT = "FREE_CREDIT"


class PaymentKind(StrEnum):
    TOPUP = "TOPUP"             # пополнение баланса
    ORDER_GROUP = "ORDER_GROUP" # оплата корзины внешним переводом


class PaymentStatus(StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"  # ждём txid от пользователя
    PENDING_VERIFY = "PENDING_VERIFY"    # txid пришёл, ждём подтверждения админом
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class DisputeStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED_REFUND = "RESOLVED_REFUND"
    RESOLVED_REJECTED = "RESOLVED_REJECTED"


class MessageKind(StrEnum):
    TEXT = "TEXT"
    PHOTO = "PHOTO"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.USER)
    courier_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    balance_usdt: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    free_credits: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    courier_city: Mapped[City | None] = relationship(foreign_keys=[courier_city_id])


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    delivery_price_usdt: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    photo_file_id: Mapped[str | None] = mapped_column(String(256))
    price_usdt: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    stock: Mapped[int] = mapped_column(Integer, default=-1)  # -1 = безлимит
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    city: Mapped[City] = relationship(foreign_keys=[city_id])


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped[Product] = relationship(foreign_keys=[product_id])


class Payment(Base):
    """Платёж: либо пополнение баланса, либо оплата группы заказов."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[PaymentKind] = mapped_column(SAEnum(PaymentKind))
    amount_usdt: Mapped[float] = mapped_column(Numeric(14, 2))
    method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod))
    txid: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING_PAYMENT)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"))
    courier_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))

    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.AWAITING_PAYMENT)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(SAEnum(PaymentMethod))
    delivery_address: Mapped[str | None] = mapped_column(Text)

    product_price_usdt: Mapped[float] = mapped_column(Numeric(12, 2))
    delivery_price_usdt: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_usdt: Mapped[float] = mapped_column(Numeric(12, 2))

    is_free: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)

    product: Mapped[Product] = relationship(foreign_keys=[product_id])
    city: Mapped[City] = relationship(foreign_keys=[city_id])
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    courier: Mapped[User | None] = relationship(foreign_keys=[courier_id])


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[MessageKind] = mapped_column(SAEnum(MessageKind), default=MessageKind.TEXT)
    text: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    moderator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[DisputeStatus] = mapped_column(SAEnum(DisputeStatus), default=DisputeStatus.OPEN)
    reason: Mapped[str] = mapped_column(Text, default="")
    resolution_note: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)


class DisputeMessage(Base):
    __tablename__ = "dispute_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispute_id: Mapped[int] = mapped_column(ForeignKey("disputes.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[MessageKind] = mapped_column(SAEnum(MessageKind), default=MessageKind.TEXT)
    text: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(Integer)  # 1..5
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    order: Mapped[Order | None] = relationship(foreign_keys=[order_id])
