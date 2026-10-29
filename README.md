# LUCAS V8.2 — Uniswap swap-event audit and diagnostics

Preserves V8.1 Kraken SMA/RSI bot, Solana/Ethereum discovery, approved dashboard and virtual-only execution.

## Corrected
- Queries **only** the full Uniswap V2 `Swap(address,uint256,uint256,uint256,uint256,address)` event topic, rather than retrieving Sync/Mint/Burn events and treating all of them as swap candidates.
- Requires exact event topic and two indexed address topics; checks the four 32-byte amount words.
- Distinguishes swap-event logs, successfully decoded swaps, rejected event formats, under-$25k swaps, risk/cooldown rejections, duplicates and virtual fills.
- Refuses to silently discard logs if a provider returns more than 250 events in a scan batch.
- Preserves the last scanned cursor until a successful scan; avoids replaying old trades after initial startup.

## Important
A previously displayed `Logs: 32, Valid swaps: 0` could simply have been 32 **Sync** events; it does not by itself prove the decoder was broken. The new counts distinguish this. Counters from earlier releases remain cumulative in their original columns; new counters begin at zero after upgrade.

The system follows public **pool-flow**, not a verified profitable trader. No Solana swap copying or verified trader P&L. No real-money trading. No trades are guaranteed. Render Free sleeps and ephemeral SQLite can reset.

## Deployment
Extract into existing GitHub project and redeploy on Render. Retain `PAPER_ADMIN_TOKEN` and optionally `LUCAS_POOL_PAPER_COPY=1` to allow pool-flow **paper-only** ETH/USD trades. No private wallets or exchange keys. View Traders & Wallets for the expanded diagnostics.
