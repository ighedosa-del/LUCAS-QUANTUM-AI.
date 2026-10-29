# LUCAS Quantum AI — Kraken Paper Research V1

A **new, independent Python/Render deployment**, with live public Kraken market quotes and closed OHLC candles. No exchange API key needed. **No live orders, no copied traders, no verified lead-trader feed, no connected account, and no realized P&L.**

## Deploy
Upload the **contents** of this folder to the root of your `LUCAS-QUANTUM-AI` GitHub repository (replace the previous version), commit to `main`. Render: Python 3, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Deploy latest commit. `render.yaml` is included.

## API
- `GET /api/kraken/markets`: public Kraken ticker, 20-second cache
- `GET /api/kraken/candles?symbol=BTC/USD&interval=5`: closed Kraken OHLC bars
- `GET /api/discovery`: explicit empty verified-trader state; Kraken public market data does **not** identify individual lead traders
- `POST /api/webhook`: authenticated signal intake; requires `WEBHOOK_TOKEN` Render secret. In-memory only; signals are not executed.
- `GET /api/demo`: legacy synthetic backtest sandbox **API only**, not shown as live trading on the dashboard.
- `POST /api/backtest`: offline research simulation, not execution.

## What is still needed for actual copy trading
An **authorized lead-trader data source** with individual trade events and 90-day daily performance history, a durable database, monitored paper-execution engine, and verification of performance before enabling any orders. Public Kraken trades alone cannot identify who traded. Never paste API keys into chat; use Render environment secrets for any future private integrations. Free Render services can sleep and cannot guarantee continuous monitoring.
