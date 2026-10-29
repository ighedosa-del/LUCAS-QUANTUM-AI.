import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd
from .core import Trader, select_traders, simulate
from . import kraken

app = FastAPI(title="CopyTrade Lab", version="0.1.0")
BASE = Path(__file__).resolve().parent

class Signal(BaseModel):
    signal_id: str = Field(min_length=1, max_length=120)
    trader_id: str = Field(min_length=1, max_length=120)
    symbol: str
    direction: str
    size: float = Field(ge=0, le=1)
    timestamp: datetime

# Ephemeral demo queue: restarts erase it. Never stores exchange credentials.
received = {}
@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status": "ok", "mode": "paper-only"}

@app.get("/api/status")
def status():
    return {"mode": "PAPER / DEMO", "received_signals": len(received),
            "live_orders_enabled": False}

@app.post("/api/webhook")
def webhook(signal: Signal, x_webhook_token: str | None = Header(default=None)):
    import hmac
    expected = os.getenv("WEBHOOK_TOKEN", "")
    if not expected or not x_webhook_token or not hmac.compare_digest(expected, x_webhook_token):
        raise HTTPException(401, "Invalid webhook token")
    if signal.timestamp.tzinfo is None:
        raise HTTPException(422, "UTC offset required")
    age = (datetime.now(timezone.utc) - signal.timestamp.astimezone(timezone.utc)).total_seconds()
    if not -5 <= age <= 60:
        raise HTTPException(422, "Stale or future signal")
    if signal.direction.upper() not in ("BUY", "SELL"):
        raise HTTPException(422, "Invalid direction")
    if signal.signal_id in received:
        return {"accepted": False, "reason": "duplicate"}
    if len(received) >= 500:
        received.clear()  # demo only; use durable storage for production
    received[signal.signal_id] = signal.model_dump(mode="json")
    return {"accepted": True, "mode": "paper-only"}

@app.get("/api/signals")
def signals():
    return list(received.values())[-20:]

@app.get("/api/demo")
def demo():
    rng = np.random.default_rng(42)
    names = ["Atlas", "Nova", "Orion", "Vega", "Pulse", "Helix", "Apex"]
    traders = []
    for i, name in enumerate(names):
        daily = pd.Series(rng.normal(0.0015 + 0.00015 * i, 0.012, 90))
        traders.append(Trader(name, daily, 100000 + i * 70000))
    traders[1].returns = traders[0].returns.copy() * 0.98 + 0.0001
    selected = select_traders(traders)
    prices = (30000 * np.exp(np.cumsum(rng.normal(0.0004, 0.013, 120)))).tolist()
    demo_signals = [{"bar": b, "direction": d, "size": 0.02}
                    for b, d in [(4,"BUY"),(16,"SELL"),(24,"BUY"),(40,"SELL"),
                                 (55,"BUY"),(70,"SELL"),(85,"BUY"),(102,"SELL")]]
    result = simulate(prices, demo_signals)
    return {"traders": selected, "backtest": result, "signals": demo_signals,
            "disclaimer": "Synthetic demonstration, not actual trader returns or investment advice."}

class BacktestRequest(BaseModel):
    prices: list[float] = Field(min_length=2, max_length=100000)
    signals: list[dict] = Field(max_length=10000)

@app.post("/api/backtest")
def backtest(payload: BacktestRequest):
    try:
        return simulate(payload.prices, payload.signals)
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        raise HTTPException(422, str(exc))

@app.get("/api/kraken/markets")
def kraken_markets():
    try:
        return {"source":"Kraken public market API", "markets":kraken.prices(), "trader_identity_available":False}
    except (OSError, ValueError, KeyError, TimeoutError) as exc:
        raise HTTPException(503, "Kraken market feed temporarily unavailable") from exc

@app.get("/api/kraken/candles")
def kraken_candles(symbol: str = "BTC/USD", interval: int = 5):
    try:
        return {"source":"Kraken public OHLC", "symbol":symbol, "interval":interval, "candles":kraken.candles(symbol,interval)}
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except (OSError, KeyError, TimeoutError) as exc:
        raise HTTPException(503,"Kraken OHLC feed temporarily unavailable") from exc

@app.get("/api/discovery")
def discovery():
    return {"status":"awaiting_authorized_trader_source", "verified_traders":[], "selected_traders":[], "max_traders":5, "requirements":{"sharpe_90d_gt":1.5,"max_drawdown_7d_gte":-0.10,"max_absolute_correlation_lt":0.9}, "note":"Kraken public trades are anonymous and cannot be attributed to individual lead traders. No trader ranking or copy trading is claimed."}

# Virtual ledger: no exchange credentials or real-money execution code.
from . import paper
class PaperOrder(BaseModel):
    symbol: str = "BTC/USD"
    side: str = "BUY"
    allocation_pct: float = Field(default=2, gt=0, le=2)
    stop_loss_pct: float = Field(default=2, ge=0.1, le=10)
    take_profit_pct: float = Field(default=4, ge=0.1, le=30)

def paper_auth(token):
    import hmac
    secret=os.getenv("PAPER_ADMIN_TOKEN", "")
    if not secret or not token or not hmac.compare_digest(secret,token):
        raise HTTPException(401,"Set PAPER_ADMIN_TOKEN in Render and provide X-Paper-Token")

@app.get('/api/paper/account')
def paper_account():
    try:
        quotes=kraken.prices()
        paper.check_stops(quotes)
        return paper.snapshot(quotes)
    except (OSError,ValueError,KeyError,TimeoutError) as exc:
        raise HTTPException(503,"Kraken quotes unavailable; paper valuations not updated") from exc

@app.post('/api/paper/order')
def paper_order(payload:PaperOrder,x_paper_token:str|None=Header(default=None)):
    paper_auth(x_paper_token)
    try:
        quotes=kraken.prices()
        paper.check_stops(quotes)
        return paper.order(payload.symbol,payload.side.upper(),payload.allocation_pct,payload.stop_loss_pct,payload.take_profit_pct,quotes)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    except (OSError,KeyError,TimeoutError) as exc: raise HTTPException(503,"Kraken quotes unavailable") from exc

# Virtual automation controls. Token never stored in the browser by the application.
from . import auto

@app.on_event("startup")
def start_auto_worker():
    auto.ensure_worker()

@app.get('/api/auto/status')
def auto_status():
    return auto.status()

@app.post('/api/auto/start')
def auto_start(x_paper_token: str | None = Header(default=None)):
    paper_auth(x_paper_token)
    return auto.set_running(True)

@app.post('/api/auto/stop')
def auto_stop(x_paper_token: str | None = Header(default=None)):
    paper_auth(x_paper_token)
    return auto.set_running(False)


@app.get('/api/auto/activity')
def auto_activity(limit: int = 50):
    return {"events": auto.activity(limit), "mode": "PAPER_ONLY"}

# Read-only Ethereum and Solana monitoring, never live execution.
from . import wallets
@app.get('/api/wallets/status')
def wallet_status():
    return wallets.snapshot()

@app.post('/api/wallets/refresh')
def wallet_refresh(x_paper_token: str | None = Header(default=None)):
    paper_auth(x_paper_token)
    return {'checks':wallets.poll(),'status':wallets.snapshot()}
