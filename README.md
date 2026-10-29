# CopyTrade Lab — Render-ready paper-trading dashboard

A **deployable research/demo application** with FastAPI, a responsive dashboard, synthetic strategy ranking, a next-bar long-only backtester, and authenticated webhook ingestion.

> **NO LIVE TRADING.** No exchange orders are sent. All dashboard performance is synthetic. This is not financial advice.

## Deploy to Render from GitHub

1. Download and extract the ZIP. Open the extracted `copytrade-render-bot` folder.
2. On GitHub choose **New repository**, then **uploading an existing file**. Drag **all files and folders inside** this folder into GitHub (including `render.yaml`), then commit. GitHub's browser uploader may require folder drag-and-drop; Git command line is more reliable for preserving nested directories.
3. In Render, choose **New → Blueprint**, connect the GitHub repository, and apply `render.yaml`.
4. Render will install Python requirements and run `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Open the generated Render URL. `/health` is the health endpoint; `/docs` is interactive API documentation.

If Blueprint is unavailable, create a Render **Web Service** using the same build and start commands.

### Local run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Run tests with `pytest -q`.

### Authenticated webhook

Set `WEBHOOK_TOKEN` in Render environment variables (Blueprint generates one).
Send a POST to `/api/webhook` with header `X-Webhook-Token: <your-secret>` and JSON:

```json
{
  "signal_id": "unique-001",
  "trader_id": "trader-A",
  "symbol": "BTC/USD",
  "direction": "BUY",
  "size": 0.02,
  "timestamp": "2026-10-29T20:16:00Z"
}
```

Use the **current UTC timestamp**, not the example timestamp. The endpoint rejects signals older than 60 seconds and duplicates. This is not directly compatible with TradingView webhook headers; a signed relay or another authentication approach is needed for TradingView.

### What is implemented

- FastAPI backend, static dashboard, Render blueprint, health checks.
- Authenticated, timestamp-validated, deduplicated signal intake (in memory).
- Research selection using 90-day Sharpe > 1.5, 7-day drawdown ≥ -10%, absolute pairwise correlation < 0.9; higher volume wins conflicts.
- Single-asset long-only paper backtest with next-bar orders, 2% cap, 0.1% fee and 0.05% slippage on each fill, equity curve, drawdown, closed-trade win rate.
- Synthetic seeded demo data and API tests.

### Not yet implemented (required before real money)

- Authorized per-trader trade/equity data feeds, live Binance/Kraken market adapters.
- Persisted signal/price/trade histories, durable idempotency, multi-worker coordination.
- Multi-trader/multi-asset accounting, capital reservation, mark-to-market, funding/FX.
- CCXT live executor, exchange precision, price-deviation checks, reconciliation, partial fills, retries, order cancelation and emergency kill switch.
- Full portfolio walk-forward validation and operational monitoring.

**Security:** Never commit exchange API secrets to GitHub. Render free instances may sleep and have ephemeral storage, so they are unsuitable for latency-sensitive or persistent live execution.

## Luxury Quantum AI dashboard

The dashboard now uses the approved black-and-gold luxury visual direction, with responsive navigation, gold equity curves, risk panels, strategy tables, and incoming signal monitoring. The visual design is **not evidence of AI predictions or live trading**. The demo figures remain synthetic.
