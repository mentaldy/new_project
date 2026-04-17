"""OpenDART filings fetcher. Maps 6-digit KRX code -> DART corp_code once, then
pulls recent disclosures for a ticker."""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx
from defusedxml import ElementTree as ET  # fallback to stdlib below if missing

try:
    from defusedxml import ElementTree as ET  # type: ignore
except ImportError:  # pragma: no cover
    import xml.etree.ElementTree as ET  # type: ignore

from .config import DATA_DIR

DART_BASE = "https://opendart.fss.or.kr/api"
CORP_CODE_CACHE = DATA_DIR / "corp_codes.xml"


@dataclass
class Filing:
    ticker: str
    rcept_no: str
    report_nm: str
    rcept_dt: str
    url: str


def _download_corp_codes(api_key: str) -> None:
    """Download and cache the DART corp_code mapping (one file, rarely changes)."""
    resp = httpx.get(
        f"{DART_BASE}/corpCode.xml", params={"crtfc_key": api_key}, timeout=30
    )
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        with zf.open("CORPCODE.xml") as f:
            CORP_CODE_CACHE.write_bytes(f.read())


def _corp_code_map(api_key: str) -> dict[str, str]:
    """Return {stock_code(6-digit): corp_code(8-digit)} for all listed companies."""
    if not CORP_CODE_CACHE.exists():
        _download_corp_codes(api_key)
    tree = ET.parse(CORP_CODE_CACHE)
    out: dict[str, str] = {}
    for row in tree.getroot().findall("list"):
        stock_code = (row.findtext("stock_code") or "").strip()
        corp_code = (row.findtext("corp_code") or "").strip()
        if stock_code and corp_code:
            out[stock_code] = corp_code
    return out


def fetch_recent_filings(
    ticker: str,
    api_key: str,
    *,
    days: int = 90,
    limit: int = 10,
) -> list[Filing]:
    """Recent DART filings for a ticker (last `days`, up to `limit`).
    Returns [] on any error — filings are enrichment, not critical path."""
    if not api_key:
        return []
    try:
        corp_map = _corp_code_map(api_key)
        corp_code = corp_map.get(ticker)
        if not corp_code:
            return []
        end = date.today()
        start = end - timedelta(days=days)
        resp = httpx.get(
            f"{DART_BASE}/list.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bgn_de": start.strftime("%Y%m%d"),
                "end_de": end.strftime("%Y%m%d"),
                "page_count": limit,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "000":
            return []
        out = []
        for row in data.get("list", [])[:limit]:
            rcept_no = row["rcept_no"]
            out.append(
                Filing(
                    ticker=ticker,
                    rcept_no=rcept_no,
                    report_nm=row["report_nm"],
                    rcept_dt=row["rcept_dt"],
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                )
            )
        return out
    except Exception:
        return []


def filings_to_prompt_block(filings: list[Filing]) -> str:
    if not filings:
        return "(최근 공시 없음 또는 조회 실패)"
    return "\n".join(
        f"- [{f.rcept_dt}] {f.report_nm} (rcept_no={f.rcept_no})" for f in filings
    )
