"""Telegram WebApp initData validation.

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InitDataError(Exception):
    pass


@dataclass(slots=True)
class InitDataUser:
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None

    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or (self.username or f"id{self.id}")


@dataclass(slots=True)
class ParsedInitData:
    user: InitDataUser
    auth_date: int
    raw: dict[str, str]


def _calc_hash(data_check_string: str, bot_token: str) -> str:
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


def parse_init_data(init_data: str, bot_token: str, *, max_age_seconds: int = 24 * 3600) -> ParsedInitData:
    """Parse and validate Telegram initData query string.

    Raises InitDataError if signature is invalid or data is too old.
    """
    if not init_data:
        raise InitDataError("empty init_data")
    if not bot_token:
        raise InitDataError("bot token is not configured on server")

    pairs = parse_qsl(init_data, keep_blank_values=True)
    raw = dict(pairs)
    received_hash = raw.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(raw.items()))
    expected_hash = _calc_hash(data_check_string, bot_token)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("hash mismatch")

    auth_date_str = raw.get("auth_date", "0")
    try:
        auth_date = int(auth_date_str)
    except ValueError as exc:
        raise InitDataError("bad auth_date") from exc

    if max_age_seconds and auth_date and time.time() - auth_date > max_age_seconds:
        raise InitDataError("init_data expired")

    user_json = raw.get("user")
    if not user_json:
        raise InitDataError("missing user")
    try:
        user_obj = json.loads(user_json)
    except json.JSONDecodeError as exc:
        raise InitDataError("bad user json") from exc

    user = InitDataUser(
        id=int(user_obj["id"]),
        username=user_obj.get("username"),
        first_name=user_obj.get("first_name"),
        last_name=user_obj.get("last_name"),
    )
    return ParsedInitData(user=user, auth_date=auth_date, raw=raw)
