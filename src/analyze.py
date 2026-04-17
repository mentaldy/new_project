"""Claude Sonnet 4.6 analysis: market data + filings + news -> structured rating."""
from __future__ import annotations

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from .config import Settings, Ticker
from .filings import Filing, filings_to_prompt_block
from .market_data import MarketSnapshot
from .news import NewsItem, news_to_prompt_block

Rating = Literal["BUY", "HOLD", "SELL"]


class Citation(BaseModel):
    source: Literal["dart_filing", "news", "market_data"]
    detail: str = Field(..., description="DART rcept_no, news title, or metric name")
    url: str | None = None


class Recommendation(BaseModel):
    ticker: str
    rating: Rating
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    thesis_ko: str = Field(..., description="2-4 sentence thesis in Korean")
    key_metrics: list[str] = Field(
        ..., description="e.g. 'PER 12.3', 'YoY 영업이익 +18%'"
    )
    target_price_krw: int | None = None
    stop_loss_krw: int | None = None
    risks: list[str] = Field(..., description="Specific downside factors")
    citations: list[Citation] = Field(
        ..., description="Every claim must cite a filing/news/metric"
    )


SYSTEM_PROMPT = """당신은 한국 주식시장(KOSPI/KOSDAQ)을 분석하는 시니어 애널리스트입니다.
개인 투자자 2명을 위한 **내부용** 분석 도구이며, 법적 책임이 있는 투자자문이 아닙니다.

각 종목에 대해 다음을 수행합니다:
1. 제공된 시장 데이터, DART 공시, 뉴스를 종합 검토.
2. BUY / HOLD / SELL 중 하나의 등급을 부여.
3. 2-4문장의 한국어 투자 논거를 제시.
4. 근거가 되는 핵심 지표를 나열(예: "PER 12.3", "YoY 영업이익 +18%").
5. 타겟 가격과 손절 가격을 원화로 제시(확신이 낮으면 null).
6. 하방 리스크를 구체적으로 3개 이내 제시.
7. **모든 주장은 citations 필드에 명시된 출처(DART 공시 rcept_no, 뉴스 제목, 또는 시장 데이터 지표)를 근거로 해야 합니다.**

원칙:
- 공시나 뉴스에 **없는** 수치를 추정하지 않습니다.
- 데이터가 부족하면 confidence를 LOW로 설정하고 HOLD를 권합니다.
- 과장된 확신은 금물. 제공된 자료로 검증 가능한 내용만 기술합니다.
- thesis_ko, key_metrics, risks는 한국어로 작성합니다."""


def _user_prompt(
    ticker: Ticker,
    market: MarketSnapshot,
    filings: list[Filing],
    news: list[NewsItem],
) -> str:
    return f"""## 분석 대상
{ticker.code} {ticker.name_ko} ({ticker.name_en})

## 시장 데이터
{market.to_prompt_block()}

## 최근 DART 공시
{filings_to_prompt_block(filings)}

## 최근 뉴스
{news_to_prompt_block(news)}

위 자료만을 근거로 {ticker.name_ko}({ticker.code})에 대한 등급과 논거를 산출하세요."""


def analyze_ticker(
    settings: Settings,
    ticker: Ticker,
    market: MarketSnapshot,
    filings: list[Filing],
    news: list[NewsItem],
    *,
    client: anthropic.Anthropic | None = None,
) -> Recommendation:
    """Run one Claude call per ticker. System prompt is cached across tickers."""
    client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.parse(
        model=settings.model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": _user_prompt(ticker, market, filings, news)}
        ],
        output_format=Recommendation,
    )
    rec = response.parsed_output
    rec.ticker = ticker.code
    return rec


class NewsSignal(BaseModel):
    compelling: bool
    reason_ko: str = Field(..., description="왜 의미있는/없는지 1-2문장")
    suggested_action: Literal["WATCH", "BUY_CANDIDATE", "SELL_CANDIDATE", "IGNORE"]


NEWS_GATE_SYSTEM = """당신은 한국 주식시장 뉴스 필터입니다.
주어진 뉴스 제목과 요약을 읽고, **매매 의사결정에 영향을 줄 만큼 의미있는 내용인지**만 판단합니다.

compelling=true 기준 (다음 중 하나 이상):
- 실적 서프라이즈 (상향/하향), 가이던스 변경
- M&A, 대형 수주, 신제품 출시
- 규제/소송/리콜 등 중대한 리스크 이벤트
- 주요 주주 지분 변동, 자사주 매입/소각

compelling=false 기준:
- 일반적인 시장 코멘트, 차트 분석, 애널리스트 의견 소개
- 이미 주가에 반영된 뻔한 내용
- 확인되지 않은 루머"""


def gate_news_item(
    settings: Settings, item: NewsItem, *, client: anthropic.Anthropic | None = None
) -> NewsSignal:
    """Cheap yes/no gate — should this news trigger a Telegram alert?"""
    client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.parse(
        model=settings.model,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": NEWS_GATE_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"종목: {item.ticker}\n"
                    f"제목: {item.title}\n"
                    f"요약: {item.summary}\n"
                    f"발행: {item.published}"
                ),
            }
        ],
        output_format=NewsSignal,
    )
    return response.parsed_output
