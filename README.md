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


## V8.3 — Configurable pool-swap threshold

The previous fixed $25,000 minimum is now configurable with `LUCAS_POOL_MIN_SWAP_USD` (default **5000**). The variable must be between **1000 and 1000000**; invalid settings are rejected rather than silently permitting unfiltered trades. The live `/api/copy/status` endpoint returns `minimum_swap_usd`, and Traders & Wallets shows the current minimum and below-threshold count. **No past swaps are back-traded or retroactively reclassified.** Previously skipped signals remain in the historical audit log.

To deploy: replace your existing project files with this ZIP and redeploy. Keep `LUCAS_POOL_PAPER_COPY=1` for optional pool-flow PAPER orders; otherwise signals are only observed. You may optionally set `LUCAS_POOL_MIN_SWAP_USD=5000` in Render, but it is already the default. No wallets, API keys or private exchange credentials required. The 30-minute cooldown, 1% per-flow allocation, position checks, stop/target, 5% drawdown breaker, and paper-only broker remain unchanged. This is an **experimental threshold**, not an empirically optimized trading strategy. More signals can increase losses. A swap signal is not a verified profitable trader.
