import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.auth import create_access_token, decode_access_token, hash_password, verify_password
from webapp.database import get_session
from webapp.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 6


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def _validate_register(data: RegisterRequest):
    if not USERNAME_RE.match(data.username):
        raise HTTPException(400, "Имя пользователя: 3-30 символов, латиница/цифры/_")
    if not EMAIL_RE.match(data.email):
        raise HTTPException(400, "Некорректный email")
    if len(data.password) < MIN_PASSWORD_LEN:
        raise HTTPException(400, f"Пароль минимум {MIN_PASSWORD_LEN} символов")


@router.post("/register")
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_session)):
    _validate_register(data)
    existing = await session.execute(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Пользователь с таким именем или email уже существует")
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        balance=1000.0,  # стартовый баланс для демо
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = create_access_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username, "balance": user.balance}}


@router.post("/login")
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Неверное имя пользователя или пароль")
    token = create_access_token(user.id, user.username)
    return {"token": token, "user": {"id": user.id, "username": user.username, "balance": user.balance}}


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Требуется авторизация")
    token = auth_header[7:]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(401, "Невалидный или просроченный токен")
    user_id = int(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "Пользователь не найден")
    return user


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "balance": user.balance,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
