"""Shared API helpers."""

from __future__ import annotations


def photo_to_url(photo: str | None) -> str | None:
    """Photos created via webapp are URLs; photos uploaded via the bot are Telegram
    file_ids and not directly fetchable here. We expose only HTTP(S) URLs to the frontend.
    """
    if not photo:
        return None
    if photo.startswith(("http://", "https://", "/")):
        return photo
    return None
