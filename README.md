# LUCAS Quantum AI V8 — Ethereum pool-flow paper signals

Built on V7. Existing dashboard, Kraken SMA/RSI paper strategy, Ethereum/Solana address discovery and watch monitoring remain.

## New, genuinely implemented
- Watches public **Uniswap V2 USDC/WETH** pool at `0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc` through Ethereum `eth_getLogs`.
- Decodes actual V2 Swap event amounts; detects ETH bought or sold against USDC; ignores ambiguous swaps.
- Deduplicates events using transaction hash and log index in SQLite. Starts from the current block on first launch: no fictional historical fills.
- `/api/copy/status` and `/api/copy/refresh` (token required for refresh) plus live signals in Traders & Wallets.
- Optional **paper-only** ETH/USD execution with `LUCAS_POOL_PAPER_COPY=1`: at most 1% virtual allocation per BUY, 2% stop, 4% target, 30-minute execution cooldown, $25k minimum observed pool swap, 5% equity drawdown guard, and position-aware sells. Default is **0 (observation only)**.

## Important limitations
This is **pool-flow following, not verified profitable-trader copy trading**. The Uniswap swap event does not establish the beneficial wallet trader's identity, wallet P&L or skill. No verified wallet ranking or Solana DEX swap-copy trading is implemented. Public Ethereum RPC providers may block `eth_getLogs`, rate-limit, or lag; the dashboard reports errors. No trades are guaranteed. The pool-flow strategy has not been backtested or demonstrated profitable. Quotes used for paper orders are live Kraken prices, not original pool execution prices. Market fees and execution simulation are simplified. Render Free can sleep and its ephemeral SQLite may reset; use persistent storage and always-on hosting for continuity. Multiple web workers must not run this daemon simultaneously.

## Deploy
1. Extract ZIP and replace your GitHub repository contents, commit, redeploy on Render.
2. Keep existing `PAPER_ADMIN_TOKEN`; no Ethereum/Solana wallet or private exchange API keys needed.
3. Optional: set `ETHEREUM_RPC_URL` to a provider that supports `eth_getLogs`. Optional: set `LUCAS_POOL_PAPER_COPY=1` in Render to permit *pool-flow paper* orders. Without it, signals are observed but never executed.
4. Press START on the dashboard. Open Traders & Wallets to inspect pool signals and reasons.

**This is not the fully requested verified-wallet copy trader.** Do not treat it as one. There is no live-money execution code.
