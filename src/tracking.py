"""Log recommendations and backfill forward returns vs KOSPI."""
from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from pykrx import stock

from .analyze import Recommendation
from .config import DATA_DIR

PICKS_CSV = DATA_DIR / "picks.csv"
FIELDS = [
    "timestamp_kst",
    "ticker",
    "rating",
    "confidence",
    "entry_price",
    "target",
    "stop",
    "thesis",
    "ret_1d",
    "ret_5d",
    "ret_20d",
    "kospi_1d",
    "kospi_5d",
    "kospi_20d",
]


def log_pick(rec: Recommendation, entry_price: float) -> None:
    PICKS_CSV.parent.mkdir(exist_ok=True)
    new_file = not PICKS_CSV.exists()
    with PICKS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(
            {
                "timestamp_kst": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ticker": rec.ticker,
                "rating": rec.rating,
                "confidence": rec.confidence,
                "entry_price": entry_price,
                "target": rec.target_price_krw or "",
                "stop": rec.stop_loss_krw or "",
                "thesis": rec.thesis_ko.replace("\n", " "),
                "ret_1d": "",
                "ret_5d": "",
                "ret_20d": "",
                "kospi_1d": "",
                "kospi_5d": "",
                "kospi_20d": "",
            }
        )


def _fwd_return(ticker: str, entry_dt: date, days: int) -> float | None:
    """Return % change vs entry price `days` trading days later, or None if not yet available."""
    end = entry_dt + timedelta(days=days * 2 + 5)  # slack for weekends/holidays
    if end > date.today():
        return None
    try:
        df = stock.get_market_ohlcv_by_date(
            entry_dt.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker
        )
        df = df[df["종가"] > 0]
        if len(df) <= days:
            return None
        entry = float(df.iloc[0]["종가"])
        later = float(df.iloc[days]["종가"])
        return (later - entry) / entry * 100 if entry else None
    except Exception:
        return None


def _kospi_return(entry_dt: date, days: int) -> float | None:
    end = entry_dt + timedelta(days=days * 2 + 5)
    if end > date.today():
        return None
    try:
        df = stock.get_index_ohlcv_by_date(
            entry_dt.strftime("%Y%m%d"), end.strftime("%Y%m%d"), "1001"
        )
        df = df[df["종가"] > 0]
        if len(df) <= days:
            return None
        return (df.iloc[days]["종가"] - df.iloc[0]["종가"]) / df.iloc[0]["종가"] * 100
    except Exception:
        return None


def backfill() -> int:
    """Recompute forward returns for all logged picks whose windows have elapsed."""
    if not PICKS_CSV.exists():
        return 0
    rows = list(csv.DictReader(PICKS_CSV.open(encoding="utf-8")))
    updated = 0
    for row in rows:
        entry_dt = datetime.strptime(row["timestamp_kst"], "%Y-%m-%d %H:%M").date()
        for days, col in [(1, "ret_1d"), (5, "ret_5d"), (20, "ret_20d")]:
            if not row[col]:
                r = _fwd_return(row["ticker"], entry_dt, days)
                if r is not None:
                    row[col] = f"{r:.2f}"
                    updated += 1
        for days, col in [(1, "kospi_1d"), (5, "kospi_5d"), (20, "kospi_20d")]:
            if not row[col]:
                r = _kospi_return(entry_dt, days)
                if r is not None:
                    row[col] = f"{r:.2f}"
    with PICKS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return updated


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        n = backfill()
        print(f"Updated {n} return cells.")
