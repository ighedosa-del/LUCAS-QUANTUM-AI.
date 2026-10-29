# LUCAS Quantum AI — Autonomous Kraken Paper V3

A clean **champagne-gold / pearl-ivory** dashboard rebuilt using the uploaded luxury dashboard as a design reference, not its unverified prediction/"entanglement" scripts. Backend is the previous Kraken V2 FastAPI paper broker plus a new automated SMA strategy. **No private Kraken credentials and no real exchange order capability.**

## Deploy to GitHub + Render

Unzip into the **root** of your `LUCAS-QUANTUM-AI` GitHub repository (not a nested folder), commit to `main`, and deploy. Keep Render Python build `pip install -r requirements.txt` and start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add a strong random `PAPER_ADMIN_TOKEN` environment variable in Render. Enter that token in the dashboard and press **START BOT**. Never paste secrets into ChatGPT or commit them to GitHub.

## What it actually does

- Polls Kraken public BTC/USD 5-minute OHLC and ticker. Uses **completed** bars only.
- Detects SMA(9)/SMA(21) crossover; buys only if RSI(14) < 70; exits on bearish crossover or 2% stop / 4% target.
- Virtual cash starts at $10,000, max 2% paper equity per entry, 0.1% simulated fees, no leverage or shorting.
- Stores paper trades and run state in SQLite. Tracks observed paper-equity peak and halts if drawdown reaches 5%. Not a guaranteed daily loss limit or continuous stop.
- Does not copy real traders. Does not promise profit. Price data is real; execution and portfolio are simulated.

## Limitations

- Render Free can sleep, so the strategy will **not** run continuously. A continuously running paid worker or always-on server is required for reliable automation.
- `/tmp` SQLite database is **ephemeral** on Render Free; redeploy/restart can erase paper account and bot state. Use persistent disk / managed DB for durable results.
- Single-process worker intended for one Uvicorn worker. Multiple app replicas/workers would run competing polling loops; don't scale horizontally without a distributed lock.
- Market polling and stop checks happen about every 65 seconds when awake; orders may slip past trigger prices. No spread/slippage modeling beyond 0.1% fees.
- UI displays only data returned by API, not fictional traders or synthetic profits.

## Tests

`pytest -q`
