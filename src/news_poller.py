"""Event-driven news alerts. Poll Naver RSS, gate new items through Claude,
Telegram only the compelling ones."""
from __future__ import annotations

import argparse
import sys

import anthropic

from . import telegram_send
from .analyze import gate_news_item
from .config import Settings, load_watchlist
from .news import fetch_news, new_items_only

ACTION_EMOJI = {
    "BUY_CANDIDATE": "🟢",
    "SELL_CANDIDATE": "🔴",
    "WATCH": "🟡",
    "IGNORE": "⚪",
}


def run(*, dry_run: bool = False) -> int:
    settings = Settings.load()
    watchlist = load_watchlist()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    name_by_code = {t.code: t.name_ko for t in watchlist}

    alerts: list[str] = []
    for ticker in watchlist:
        items = fetch_news(ticker.code, limit=10)
        fresh = new_items_only(items)
        for item in fresh:
            try:
                signal = gate_news_item(settings, item, client=client)
            except Exception as e:
                print(f"  {ticker.code} gate error: {e}", file=sys.stderr)
                continue
            if signal.compelling:
                emoji = ACTION_EMOJI.get(signal.suggested_action, "⚪")
                alerts.append(
                    f"{emoji} *{name_by_code[ticker.code]}* (`{ticker.code}`) — {signal.suggested_action}\n"
                    f"*{item.title}*\n"
                    f"{signal.reason_ko}\n"
                    f"[link]({item.link})"
                )

    if not alerts:
        print("No compelling news this cycle.")
        return 0

    body = "*🚨 실시간 뉴스 알림*\n\n" + "\n\n".join(alerts)
    telegram_send.send(settings, body, dry_run=dry_run)
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
