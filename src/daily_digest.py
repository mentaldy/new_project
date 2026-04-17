"""Daily pre-market run: fetch -> analyze -> Telegram -> log."""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime

import anthropic

from . import telegram_send, tracking
from .analyze import Recommendation, analyze_ticker
from .config import Settings, load_watchlist
from .filings import fetch_recent_filings
from .market_data import fetch_kospi_change, fetch_snapshot
from .news import fetch_news

RATING_EMOJI = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}


def _format_digest(recs: list[tuple[str, Recommendation]], kospi_chg: float) -> str:
    lines = [
        f"*📊 일일 종목 분석 — {datetime.now():%Y-%m-%d %H:%M KST}*",
        f"KOSPI 전일 대비: `{kospi_chg:+.2f}%`",
        "",
    ]
    buys = [r for _, r in recs if r.rating == "BUY"]
    sells = [r for _, r in recs if r.rating == "SELL"]
    if buys:
        lines.append("*🟢 매수 후보*")
        for r in buys:
            lines.append(f"• `{r.ticker}` — {r.confidence}")
            lines.append(f"  {r.thesis_ko}")
        lines.append("")
    if sells:
        lines.append("*🔴 매도 후보*")
        for r in sells:
            lines.append(f"• `{r.ticker}` — {r.confidence}")
            lines.append(f"  {r.thesis_ko}")
        lines.append("")
    lines.append("*📋 전체 평가*")
    for name, r in recs:
        lines.append(f"{RATING_EMOJI[r.rating]} `{r.ticker}` {name} — {r.rating}")
    return "\n".join(lines)


def run(*, dry_run: bool = False) -> int:
    settings = Settings.load()
    watchlist = load_watchlist()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        kospi_chg = fetch_kospi_change()
    except Exception:
        kospi_chg = float("nan")

    results: list[tuple[str, Recommendation]] = []
    for ticker in watchlist:
        try:
            market = fetch_snapshot(ticker.code)
            filings = fetch_recent_filings(ticker.code, settings.dart_api_key)
            news = fetch_news(ticker.code)
            rec = analyze_ticker(settings, ticker, market, filings, news, client=client)
            results.append((ticker.name_ko, rec))
            tracking.log_pick(rec, entry_price=market.last_close)
            print(f"  {ticker.code} {ticker.name_ko}: {rec.rating} ({rec.confidence})")
        except Exception as e:
            print(f"  {ticker.code} {ticker.name_ko}: ERROR — {e}", file=sys.stderr)
            traceback.print_exc()

    if not results:
        print("No recommendations produced; skipping Telegram.", file=sys.stderr)
        return 1

    telegram_send.send(settings, _format_digest(results, kospi_chg), dry_run=dry_run)
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
