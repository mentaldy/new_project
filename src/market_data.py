"""Market data via pykrx. OHLCV + fundamentals for a ticker."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from pykrx import stock


@dataclass
class MarketSnapshot:
    code: str
    as_of: str
    last_close: float
    chg_pct_1d: float
    chg_pct_5d: float
    chg_pct_20d: float
    volume: int
    market_cap_krw: int | None
    per: float | None
    pbr: float | None
    eps: float | None
    bps: float | None
    dividend_yield: float | None

    def to_prompt_block(self) -> str:
        return (
            f"가격(as of {self.as_of}): {self.last_close:,.0f}원 "
            f"(1d {self.chg_pct_1d:+.2f}%, 5d {self.chg_pct_5d:+.2f}%, 20d {self.chg_pct_20d:+.2f}%)\n"
            f"거래량: {self.volume:,} | 시총: "
            f"{self.market_cap_krw:,}원\n" if self.market_cap_krw else ""
        ) + (
            f"PER: {self.per} | PBR: {self.pbr} | EPS: {self.eps} | "
            f"BPS: {self.bps} | 배당수익률: {self.dividend_yield}%"
        )


def _last_business_day(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _fetch_ohlcv(code: str, s: str, e: str) -> pd.DataFrame:
    """Try stock OHLCV first; fall back to ETF OHLCV (different pykrx endpoint)."""
    try:
        df = stock.get_market_ohlcv_by_date(s, e, code)
        df = df[df["시가"] > 0] if not df.empty else df
        if not df.empty:
            return df
    except Exception:
        pass
    try:
        df = stock.get_etf_ohlcv_by_date(s, e, code)
        if not df.empty and "종가" in df.columns:
            df = df[df["종가"] > 0]
            return df
    except Exception:
        pass
    return pd.DataFrame()


def fetch_snapshot(code: str, asof: date | None = None) -> MarketSnapshot:
    """Fetch OHLCV + fundamentals for a KRX ticker (works for stocks and ETFs)."""
    asof = _last_business_day(asof or date.today())
    start = asof - timedelta(days=40)  # enough for 20-day returns incl. holidays
    s, e = start.strftime("%Y%m%d"), asof.strftime("%Y%m%d")

    ohlcv = _fetch_ohlcv(code, s, e)
    if ohlcv.empty:
        raise RuntimeError(f"No OHLCV for {code} in {s}-{e}")

    last = ohlcv.iloc[-1]
    close = float(last["종가"])

    def pct(days_back: int) -> float:
        if len(ohlcv) <= days_back:
            return float("nan")
        prev = float(ohlcv.iloc[-1 - days_back]["종가"])
        return (close - prev) / prev * 100 if prev else float("nan")

    try:
        fund = stock.get_market_fundamental_by_date(s, e, code)
        fund_last = fund.iloc[-1] if not fund.empty else None
    except Exception:
        fund_last = None  # ETFs / unsupported tickers have no fundamentals

    try:
        cap_df = stock.get_market_cap_by_date(s, e, code)
        cap = int(cap_df.iloc[-1]["시가총액"]) if not cap_df.empty else None
    except Exception:
        cap = None

    return MarketSnapshot(
        code=code,
        as_of=asof.strftime("%Y-%m-%d"),
        last_close=close,
        chg_pct_1d=pct(1),
        chg_pct_5d=pct(5),
        chg_pct_20d=pct(20),
        volume=int(last["거래량"]),
        market_cap_krw=cap,
        per=float(fund_last["PER"]) if fund_last is not None else None,
        pbr=float(fund_last["PBR"]) if fund_last is not None else None,
        eps=float(fund_last["EPS"]) if fund_last is not None else None,
        bps=float(fund_last["BPS"]) if fund_last is not None else None,
        dividend_yield=float(fund_last["DIV"]) if fund_last is not None else None,
    )


def fetch_kospi_change(asof: date | None = None) -> float:
    """1-day KOSPI index change %, for digest header context."""
    asof = _last_business_day(asof or date.today())
    start = asof - timedelta(days=5)
    df = stock.get_index_ohlcv_by_date(
        start.strftime("%Y%m%d"), asof.strftime("%Y%m%d"), "1001"
    )
    df = df[df["종가"] > 0]
    if len(df) < 2:
        return float("nan")
    return (df.iloc[-1]["종가"] - df.iloc[-2]["종가"]) / df.iloc[-2]["종가"] * 100
