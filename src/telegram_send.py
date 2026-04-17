"""Telegram Bot API sender. Fan-out to all configured chat IDs."""
from __future__ import annotations

import httpx

from .config import Settings

API = "https://api.telegram.org/bot{token}/sendMessage"


def send(settings: Settings, text: str, *, dry_run: bool = False) -> None:
    if dry_run or not settings.telegram_bot_token:
        print("--- [telegram dry-run] ---")
        print(text)
        print("--------------------------")
        return
    url = API.format(token=settings.telegram_bot_token)
    for chat_id in settings.telegram_chat_ids:
        # Telegram caps messages at 4096 chars — split defensively.
        for chunk in _chunks(text, 4000):
            httpx.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            ).raise_for_status()


def _chunks(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    out = []
    cur = ""
    for line in text.splitlines(keepends=True):
        if len(cur) + len(line) > size:
            out.append(cur)
            cur = line
        else:
            cur += line
    if cur:
        out.append(cur)
    return out
