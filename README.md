# LUCAS Quantum AI V6 — Ethereum & Solana Wallet Monitor

Extends the V5 black/gold dashboard and existing Kraken SMA/RSI autonomous paper bot. No live exchange execution.

## Included
- Ethereum mainnet ERC-20 **transfer observations** from Routescan's keyless Etherscan-compatible API.
- Solana confirmed transaction **signatures** using JSON-RPC `getSignaturesForAddress`.
- SQLite event deduplication, per-wallet polling state, and transparent errors.
- Background wallet polling every 5 minutes **while the existing paper bot is running**.
- `GET /api/wallets/status`, authenticated `POST /api/wallets/refresh`.
- Trader & Wallets dashboard displays configured addresses and actual observed events.
- Preserves V5 Kraken paper strategy, activity history and START/STOP.

## Render configuration
1. Replace your GitHub project with these files, commit and redeploy.
2. Keep `PAPER_ADMIN_TOKEN` set.
3. Optional: set `LUCAS_WATCH_WALLETS` to comma-separated public addresses, e.g. `ethereum:0xYOUR40HEXADDRESS,solana:YOURPUBLICBASE58ADDRESS`. These are watch addresses, **not** private keys.
4. Optional: set `SOLANA_RPC_URL` to a trusted dedicated RPC URL for reliable monitoring. Never place secrets in the frontend or GitHub.
5. Press START. Monitoring runs only while the instance and paper bot are running.

## Scope and limits
**This is a real read-only data integration, not a verified wallet copy-trading engine.** It does not automatically discover profitable traders, reconstruct DEX swaps, compute trustworthy wallet returns, or place paper-copy orders. Ethereum ERC-20 transfers are not equivalent to trades; Solana signatures do not reveal token swaps without further transaction parsing. No false signals, returns or rankings are generated. A future release needs historical DEX indexing, token mapping, fee/slippage reconstruction and forward validation before automatic wallet-copy execution.

Public Solana RPC is rate-limited and unsuitable for reliable 24/7 monitoring; Render Free may sleep and its local SQLite storage is ephemeral. Use a persistent disk/DB and always-on instance for continuous operation.

## Run
`pip install -r requirements.txt`
`uvicorn app.main:app --host 0.0.0.0 --port 8000`
`python -m pytest -q`
