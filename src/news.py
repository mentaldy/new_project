"""Naver Finance news per ticker via RSS. Dedupes seen items across runs."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import feedparser

from .config import DATA_DIR

SEEN_PATH = DATA_DIR / "seen_news.json"


@dataclass
class NewsItem:
    ticker: str
    title: str
    link: str
    published: str
    summary: str

    @property
    def id(self) -> str:
        return hashlib.sha1(f"{self.ticker}|{self.link}".encode()).hexdigest()


def _load_seen() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        return set(json.loads(SEEN_PATH.read_text()))
    except Exception:
        return set()


def _save_seen(seen: set[str]) -> None:
    SEEN_PATH.write_text(json.dumps(sorted(seen)))


def fetch_news(ticker: str, *, limit: int = 10) -> list[NewsItem]:
    """Pull recent Korean news for a KRX ticker from Naver Finance RSS."""
    url = f"https://finance.naver.com/item/news_news.naver?code={ticker}&output=rss"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    out: list[NewsItem] = []
    for entry in feed.entries[:limit]:
        out.append(
            NewsItem(
                ticker=ticker,
                title=getattr(entry, "title", "").strip(),
                link=getattr(entry, "link", ""),
                published=getattr(entry, "published", ""),
                summary=getattr(entry, "summary", "")[:500],
            )
        )
    return out


def new_items_only(items: list[NewsItem]) -> list[NewsItem]:
    """Filter to unseen items, then persist IDs so next run won't re-alert."""
    seen = _load_seen()
    fresh = [it for it in items if it.id not in seen]
    if fresh:
        seen.update(it.id for it in fresh)
        _save_seen(seen)
    return fresh


def news_to_prompt_block(items: list[NewsItem], max_items: int = 5) -> str:
    if not items:
        return "(최근 뉴스 없음)"
    return "\n".join(
        f"- [{it.published}] {it.title}" for it in items[:max_items]
    )
