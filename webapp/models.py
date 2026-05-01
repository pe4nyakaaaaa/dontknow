import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    balance = Column(Float, default=0.0)
    avatar_url = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    inventory = relationship("UserInventory", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    tickets = relationship("SupportTicket", back_populates="user")


class Skin(Base):
    __tablename__ = "skins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    weapon = Column(String(100), nullable=False)
    rarity = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    color = Column(String(7), default="#ffffff")
    image_url = Column(String(500), default="")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String(500), default="")
    description = Column(Text, default="")
    category = Column(String(50), default="standard")

    items = relationship("CaseSkin", back_populates="case")


class CaseSkin(Base):
    __tablename__ = "case_skins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    skin_id = Column(Integer, ForeignKey("skins.id"), nullable=False)
    drop_weight = Column(Float, nullable=False, default=1.0)

    case = relationship("Case", back_populates="items")
    skin = relationship("Skin")


class UserInventory(Base):
    __tablename__ = "user_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skin_id = Column(Integer, ForeignKey("skins.id"), nullable=False)
    obtained_at = Column(DateTime, default=datetime.datetime.utcnow)
    obtained_from = Column(String(200), default="")

    user = relationship("User", back_populates="inventory")
    skin = relationship("Skin")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    transaction_id = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="payments")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(300), nullable=False)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="tickets")
    messages = relationship("SupportMessage", back_populates="ticket")


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    message = Column(Text, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    ticket = relationship("SupportTicket", back_populates="messages")
