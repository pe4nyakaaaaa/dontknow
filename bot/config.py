"""Конфигурация бота: токен, роли, кошельки, БД."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_id_list(raw: str | None) -> set[int]:
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


@dataclass(slots=True)
class Settings:
    bot_token: str
    owner_id: int
    admin_ids: set[int]
    moderator_ids: set[int]
    ton_wallet: str
    usdt_trc20_wallet: str
    database_url: str
    sql_echo: bool = False
    bot_name: str = "🛒 Auto-Sales"

    @classmethod
    def load(cls) -> Settings:
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token or token.startswith("123456:"):
            # допускаем плейсхолдер только для импорт-теста; в проде упадёт ниже при старте polling.
            pass

        owner = int(os.getenv("OWNER_ID", "0") or "0")
        admins = _parse_id_list(os.getenv("ADMIN_IDS"))
        mods = _parse_id_list(os.getenv("MODERATOR_IDS"))
        if owner:
            admins.add(owner)
            mods.add(owner)

        return cls(
            bot_token=token,
            owner_id=owner,
            admin_ids=admins,
            moderator_ids=mods,
            ton_wallet=os.getenv("TON_WALLET", "").strip(),
            usdt_trc20_wallet=os.getenv("USDT_TRC20_WALLET", "").strip(),
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db"),
            sql_echo=os.getenv("SQL_ECHO", "0") == "1",
        )

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids or user_id == self.owner_id

    def is_moderator(self, user_id: int) -> bool:
        return user_id in self.moderator_ids or self.is_admin(user_id)


# глобальный синглтон, удобно импортировать в хэндлерах.
settings: Settings = Settings.load()
