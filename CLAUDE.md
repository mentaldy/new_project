# Korean Stock Analyzing & Reporting App

## Project Overview
Internal AI-powered stock + ETF recommendation tool for the Korean market (KOSPI/KOSDAQ, including KR-listed ETFs with foreign exposure). Screens a curated watchlist, generates Buy/Hold/Sell ratings with thesis/risks/citations using Claude Sonnet 4.6, and delivers digests via **Telegram** on a daily pre-market schedule plus event-driven news alerts. Orchestrated via **GitHub Actions cron**.

Scope note: US-listed names (NYSE/NASDAQ) are out of scope for MVP. Korean investors can still get US exposure via KR-listed ETFs (e.g. TIGER 미국S&P500, TIGER 미국나스닥100).

## Status
MVP scaffolding in place. Needs API keys + first live run.

## Users
- 2 internal users only. No 유사투자자문업 신고 required.

## Runtime Model
**Not Claude Code orchestrated.** Python scripts triggered by GitHub Actions cron. Claude Sonnet 4.6 is called via the Anthropic SDK from inside the analysis step. Continuous operation comes from GHA, not from a live Claude session.

## Cadence
- **Daily pre-market digest**: GHA cron `0 22 * * 0-4` (UTC) = 07:00 KST weekdays.
- **News poller**: GHA cron `*/15 0-6 * * 1-5` (UTC) = every 15 min during KST market hours.

## Architecture

### Data Sources (free)
- **pykrx** — OHLCV, market cap, PER/PBR, foreign ownership.
- **OpenDART API** — filings (사업보고서, 분기/반기보고서), 공시.
- **Naver Finance RSS** — Korean news per ticker.

### Modules (`src/`)
| File | Responsibility |
|---|---|
| `config.py` | Load env vars + `config/watchlist.yaml` |
| `market_data.py` | pykrx fetchers (OHLCV, fundamentals) |
| `filings.py` | OpenDART recent filings per ticker |
| `news.py` | Naver RSS news per ticker, with dedup state |
| `analyze.py` | Claude Sonnet 4.6 with structured output (Pydantic) |
| `telegram_send.py` | Telegram Bot API sender |
| `tracking.py` | Log picks to CSV, compute forward returns |
| `daily_digest.py` | Orchestrates the full daily run |
| `news_poller.py` | Orchestrates the news-driven alert run |

### LLM Call Design
- Model: `claude-sonnet-4-6`.
- Adaptive thinking + `effort: high` (Sonnet 4.6 supports both).
- **Prompt caching** on the stable system prompt (rules, output schema guidance). Volatile ticker-specific data goes after the cache breakpoint.
- Structured output via `client.messages.parse(output_format=Recommendation)` — Pydantic schema enforces `rating`, `confidence`, `thesis`, `target_price_krw`, `stop_loss_krw`, `risks`, `citations`.
- Per-ticker calls (not one big call) for focused reasoning and easy per-ticker retry.

### Delivery
- Telegram Bot API. Create a bot via `@BotFather`, put `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS` (comma-separated) in GHA secrets.
- Telegram chosen over Kakao: no business registration, no template approval, works for 2 internal users instantly.
- Kakao integration deferred to post-MVP.

### Pick Tracking
- `data/picks.csv` logs every rec with `timestamp_kst, ticker, rating, confidence, entry_price, thesis_hash`.
- Daily job backfills 1D/1W/1M forward returns vs KOSPI benchmark.

## Key Risks
1. **LLM hallucination on 재무제표** — structured schema requires DART filing citations + specific metric values.
2. **Pick quality measurement** — tracking writes from day 1.
3. **Data staleness** — DART is infrequent, after-hours prices stale. Every rec timestamps data recency.
4. **LLM cost drift** — per-ticker calls on ~30 names ≈ $10-30/month. If universe grows to 100+, pre-filter with Haiku 4.5, escalate to Sonnet 4.6 on candidates only.

## Setup

### Secrets required (GitHub Actions Secrets)
- `ANTHROPIC_API_KEY` — Anthropic console.
- `DART_API_KEY` — opendart.fss.or.kr (free, 5-min registration).
- `TELEGRAM_BOT_TOKEN` — @BotFather.
- `TELEGRAM_CHAT_IDS` — comma-separated chat IDs (get from bot after /start).

### Local dev
```bash
pip install -e .
cp .env.example .env   # fill in keys
python -m src.daily_digest --dry-run
python -m src.news_poller --dry-run
```

### GitHub Actions
Workflows live under `.github/workflows/`. Enable Actions, add the 4 secrets above, push to `main`. Cron kicks in automatically.

## Roadmap
- **Week 1** (current): scaffold + first live daily run.
- **Week 2**: news poller + forward-return tracking dashboard.
- **Post-MVP**: Kakao delivery, web dashboard, larger universe, backtesting.

## Open Decisions
- [ ] Confirm seed watchlist (default is 30 KOSPI blue-chips in `config/watchlist.yaml`).
- [ ] Register OpenDART API key.
- [ ] Create Telegram bot, get chat IDs for both users.

## Development Commands
```bash
python -m src.daily_digest              # live run
python -m src.daily_digest --dry-run    # no Telegram send, prints to stdout
python -m src.news_poller               # live run
python -m src.news_poller --dry-run
python -m src.tracking backfill         # compute forward returns on logged picks
```
