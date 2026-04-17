# Korean Stock Analyzing & Reporting App

## Project Overview
Internal AI-powered stock recommendation tool for the Korean market (KOSPI/KOSDAQ). The system screens a curated watchlist of ~50-100 tickers, generates Buy/Hold/Sell ratings with thesis/risks/citations using Claude Sonnet 4.6, and delivers digests via KakaoTalk on a daily pre-market schedule plus event-driven news alerts.

## Status
Planning complete. MVP prototype target: 1-2 weeks. Phase 1 development next.

## Users
- 2 internal users only. Not offered to the public.
- No 유사투자자문업 신고 required (applies only to public-facing advisory services).
- If we ever open to external users, regulatory posture must be revisited.

## MVP Scope

### Output
- For each watchlist ticker: `{rating: BUY|HOLD|SELL, thesis, target_price, stop_loss, risks, citations}`
- Citations must reference the specific DART filing URL and metrics used, so every rec is auditable.

### Cadence
- **Daily pre-market digest** (~07:00 KST): full watchlist scored, Kakao summary sent.
- **Event-driven alerts**: news poller (every 15 min) gates candidate items through Claude ("is this materially compelling?"); if yes, push Kakao alert.

### Universe
- Curated watchlist of ~50-100 Korean tickers.
- Seed from KOSPI 100; maintained in `config/watchlist.yaml`.
- User edits the list over time based on portfolio interest.

## Architecture

### Data Sources (all free)
- **pykrx** — OHLCV, market cap, PER/PBR/PSR, foreign ownership, KOSPI/KOSDAQ indices.
- **OpenDART API** — quarterly/annual filings (사업보고서, 분기/반기보고서), 공시.
- **FinanceDataReader** — backup price source.
- **Naver Finance / 연합뉴스 RSS** — Korean news per ticker (respect ToS, cache).

### Recommendation Engine (Python)
```
src/
  fetch_watchlist.py   # load config/watchlist.yaml
  fetch_market_data.py # pykrx daily OHLCV + fundamentals
  fetch_filings.py     # OpenDART recent filings per ticker
  fetch_news.py        # news per ticker (cached, deduped)
  analyze.py           # Claude Sonnet 4.6, structured output schema
  format_report.py     # Korean-language digest for Kakao
  send_kakao.py        # Kakao Login "나에게 보내기" API
  track_picks.py       # log recs + compute forward returns vs KOSPI
```

### Orchestration
- **Cloud Run Jobs** (GCP) scheduled via Cloud Scheduler:
  - `daily-digest` — 07:00 KST weekdays.
  - `news-poller` — every 15 min during market hours.
- Secrets (Anthropic API key, DART key, Kakao tokens) in Secret Manager.

### Delivery (KakaoTalk)
- **Primary**: Kakao Login OAuth per user → "나에게 보내기" Message API. Each user authorizes once; refresh tokens stored in Secret Manager.
- **Fallback**: If Kakao integration slips, ship prototype on Telegram and swap in Kakao for v1.1.

### Pick Tracking
- Every recommendation logged to a persistent store (Firestore or Google Sheet) with `ticker, timestamp, rating, entry_price, thesis_hash`.
- Daily job computes 1D / 1W / 1M forward returns vs KOSPI benchmark.
- This tracking is non-negotiable — it's how we know whether the AI is actually good.

## Tech Stack
- **Language**: Python 3.12
- **Core libs**: pykrx, dart-fss (or OpenDART SDK), FinanceDataReader, pandas, httpx, pydantic
- **LLM**: Anthropic SDK (Claude Sonnet 4.6), structured output via tool use
- **Hosting**: GCP Cloud Run Jobs + Cloud Scheduler + Secret Manager + Firestore
- **Config**: YAML for watchlist, `.env` for local dev

## Key Risks (tracked)
1. **Kakao delivery complexity** — "나에게 보내기" works for personal accounts but token refresh is finicky. Telegram fallback ready.
2. **LLM hallucination on 재무제표** — mitigated via structured output requiring DART citation + specific metric values.
3. **Pick quality measurement** — tracking infra must ship on day 1, not day 14.
4. **Data staleness** — DART filings are infrequent, after-hours prices are stale. Every rec timestamps data recency.
5. **LLM cost drift** — daily 100-stock scoring can get pricey. Use Haiku pre-filter → Sonnet deep-dive on candidates only, if cost becomes an issue.

## Roadmap

### Week 1 — Data + Recommendation Core
- Repo scaffold, `.env`/secrets, Python project setup.
- `fetch_market_data.py` via pykrx.
- `fetch_filings.py` via OpenDART (get API key).
- `fetch_news.py` (Naver + RSS).
- `analyze.py` Claude prompt + structured output schema.
- CLI end-to-end run: `python -m src.daily_digest --dry-run`.

### Week 2 — Delivery + Tracking + Deploy
- Kakao OAuth flow, token storage, `send_kakao.py`.
- `track_picks.py` + forward-return cron.
- Cloud Run Jobs + Scheduler setup.
- News poller + event-driven alert gate.
- First live run with real watchlist.

### Post-MVP (if picks prove valuable)
- Web dashboard (Next.js) for rec history and performance charts.
- Expand universe to full KOSPI/KOSDAQ.
- Backtesting framework.
- Evaluate regulatory path if external users are requested.

## Open Decisions
- [ ] Confirm seed watchlist (start from KOSPI 100 or your own list).
- [ ] OpenDART API key registration.
- [ ] Kakao Developers app registration (both users).
- [ ] GCP project + billing.

## Development Commands
_TBD once scaffold exists._
