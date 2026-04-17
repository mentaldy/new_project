"""Environment + watchlist loading."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
WATCHLIST_PATH = ROOT / "config" / "watchlist.yaml"


@dataclass(frozen=True)
class Ticker:
    code: str
    name_ko: str
    name_en: str
    asset_type: str = "stock"  # "stock" or "etf"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    dart_api_key: str
    telegram_bot_token: str
    telegram_chat_ids: list[str]
    model: str = "claude-sonnet-4-6"

    @classmethod
    def load(cls) -> "Settings":
        ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "")
        chat_ids = [cid.strip() for cid in ids_raw.split(",") if cid.strip()]
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            dart_api_key=os.getenv("DART_API_KEY", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_ids=chat_ids,
        )


def load_watchlist() -> list[Ticker]:
    data = yaml.safe_load(WATCHLIST_PATH.read_text(encoding="utf-8"))
    return [Ticker(**t) for t in data["tickers"]]
