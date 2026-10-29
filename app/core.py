"""Deterministic research utilities. No live execution."""
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

@dataclass
class Trader:
    trader_id: str
    returns: pd.Series
    volume_usd: float

def metrics(returns: pd.Series):
    r = pd.Series(returns, dtype=float).dropna()
    if len(r) < 2 or (r <= -1).any():
        return {"sharpe": None, "drawdown": None}
    sd = r.std()
    sharpe = float(np.sqrt(365) * r.mean() / sd) if sd > 0 else None
    equity = (1 + r).cumprod()
    dd = float((equity / equity.cummax() - 1).min())
    return {"sharpe": sharpe, "drawdown": dd}

def select_traders(traders: list[Trader], max_count=5):
    """Requires full 90 daily returns; 7-day drawdown starts at window's first return."""
    eligible = []
    for t in traders:
        r = t.returns
        if len(r) != 90 or r.isna().any() or (r <= -1).any():
            continue
        m = metrics(r)
        dd7 = metrics(r.iloc[-7:])["drawdown"]
        if m["sharpe"] is not None and m["sharpe"] > 1.5 and dd7 >= -0.10 and t.volume_usd > 0:
            eligible.append((t, m["sharpe"], dd7))
    eligible.sort(key=lambda x: (-x[0].volume_usd, -x[1], x[0].trader_id))
    selected = []
    for item in eligible:
        t = item[0]
        if all(
            (not np.isfinite(t.returns.corr(s[0].returns))) is False
            and abs(t.returns.corr(s[0].returns)) < 0.90
            for s in selected
        ):
            selected.append(item)
    selected.sort(key=lambda x: -x[1])
    return [
        {"trader_id": t.trader_id, "sharpe": round(sh, 3),
         "drawdown_7d": round(dd, 4), "volume_usd": t.volume_usd}
        for t, sh, dd in selected[:max_count]
    ]

def simulate(prices: list[float], signals: list[dict], initial_cash=10000.0,
             fee=0.001, slippage=0.0005, max_allocation=0.02):
    """Single-asset, long-only next-bar paper backtest. size is target equity fraction.
    signal.bar is detection bar; order executes at bar+1.
    Fee and slippage applied on entry AND exit; last position marked to market.
    """
    if not prices or any(not math.isfinite(p) or p <= 0 for p in prices):
        raise ValueError("Prices must be positive finite numbers")
    events = {}
    for s in signals:
        bar = int(s["bar"]) + 1
        if bar < 1 or bar >= len(prices):
            continue
        direction = s["direction"].upper()
        if direction not in ("BUY", "SELL"):
            raise ValueError("direction must be BUY or SELL")
        events[bar] = (direction, float(s.get("size", max_allocation)))
    cash = float(initial_cash)
    qty = 0.0
    entry_cost = 0.0
    pnl = []
    equity = []
    for bar, price in enumerate(prices):
        if bar in events:
            direction, size = events[bar]
            if direction == "SELL" and qty:
                proceeds = qty * price * (1 - slippage) * (1 - fee)
                cash += proceeds
                pnl.append(proceeds - entry_cost)
                qty, entry_cost = 0.0, 0.0
            elif direction == "BUY" and qty == 0:
                # cap total spend INCLUDING fees, using current marked equity
                budget = min(max(size, 0.0), max_allocation) * (cash + qty * price)
                qty = budget / (price * (1 + slippage) * (1 + fee))
                entry_cost = budget
                cash -= budget
        equity.append(cash + qty * price)
    peak = np.maximum.accumulate(equity)
    dd = np.array(equity) / peak - 1
    return {
        "equity_curve": [round(x, 2) for x in equity],
        "max_drawdown": round(float(dd.min()), 5),
        "win_rate": round(sum(p > 0 for p in pnl) / len(pnl), 4) if pnl else None,
        "closed_trades": len(pnl),
        "total_return": round(equity[-1] / initial_cash - 1, 5),
        "open_position": qty > 0,
    }
