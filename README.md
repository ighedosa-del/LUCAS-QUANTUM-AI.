# LUCAS Quantum AI V7 — public-chain discovery (paper only)

Preserves the V6 black-and-gold dashboard, Kraken SMA/RSI paper strategy, activity log, virtual account and START/STOP.

## New in V7

- Ethereum: samples the latest public block and extracts sender/receiver addresses.
- Solana: samples a finalized public block and extracts transaction signers.
- SQLite deduplication and observation counts; up to 3,000 recent candidate addresses.
- Runs automatically approximately every 10 minutes while START is active and the Render service is awake.
- `GET /api/discovery/v7` shows honest discovery status, candidates and provider errors.
- `POST /api/discovery/v7/refresh` requires the same `X-Paper-Token` as START.
- Traders & Wallets dashboard shows candidate observations and errors.
- Optional `ETHEREUM_RPC_URL` and `SOLANA_RPC_URL` for dedicated providers.

## What this does NOT do

An observed wallet address is **not a verified profitable trader**. V7 does not yet reconstruct swaps, calculate verified P&L, automatically select profitable wallets, or copy trade. These features remain disabled, and no fictional returns are displayed. Sampling blocks is discovery of *active addresses*, not proof of trading skill. RPC public providers can restrict full block access, especially Solana `getBlock`; provider errors are displayed, not hidden.

## Deploy

Replace V6 GitHub project contents with the ZIP contents and redeploy Render. Keep `PAPER_ADMIN_TOKEN`. No private wallet keys, Kraken exchange credentials or blockchain signing required. For stable block queries set dedicated provider URLs in Render environment variables. The free Render tier can sleep, and local SQLite state is ephemeral unless persistent storage is configured. Avoid multiple worker processes with this SQLite/daemon design.

## Start

`pip install -r requirements.txt`

`uvicorn app.main:app --host 0.0.0.0 --port 8000`

`python -m pytest -q`

**Paper simulation only; not investment advice or evidence of profitable strategy.**
