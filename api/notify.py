"""Send Telegram messages from the API via Bot API."""

from __future__ import annotations

import logging

import httpx

from bot.config import settings

log = logging.getLogger(__name__)


async def send_message(chat_id: int, text: str) -> None:
    if not settings.bot_token:
        log.warning("BOT_TOKEN not set, skipping notification to %s", chat_id)
        return
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception as exc:  # noqa: BLE001
        log.warning("Telegram notify failed for %s: %s", chat_id, exc)
