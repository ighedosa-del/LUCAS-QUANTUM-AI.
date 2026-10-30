"""Durable virtual-only broker. No private Kraken API and no live order capability."""
import os, sqlite3, threading, time
from contextlib import contextmanager
from pathlib import Path

STARTING_CASH = 10_000.0
FEE_RATE = 0.001
MAX_ALLOCATION = 0.02
MAX_OPEN = 5
ALLOWED = {"BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD"}
DB = Path(os.getenv("PAPER_DB_PATH", "/tmp/lucas-paper.sqlite3"))
LOCK = threading.RLock()

@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB), timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA busy_timeout=10000")
        con.execute("CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY CHECK(id=1), cash REAL NOT NULL, initial REAL NOT NULL)")
        con.execute("INSERT OR IGNORE INTO account(id,cash,initial) VALUES(1,?,?)", (STARTING_CASH,STARTING_CASH))
        con.execute("CREATE TABLE IF NOT EXISTS positions (symbol TEXT PRIMARY KEY, quantity REAL NOT NULL, entry REAL NOT NULL, cost REAL NOT NULL, stop REAL NOT NULL, target REAL, opened REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS fills (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, side TEXT NOT NULL, quantity REAL NOT NULL, price REAL NOT NULL, fee REAL NOT NULL, pnl REAL, reason TEXT NOT NULL, created REAL NOT NULL)")
        con.commit()
        yield con
    finally:
        con.close()

def _positive_price(prices, symbol):
    quote = prices.get(symbol)
    if not quote:
        raise ValueError("No current Kraken quote for this symbol")
    price = float(quote["last"])
    if not (0 < price < 1e12):
        raise ValueError("Invalid Kraken price")
    return price

def snapshot(prices):
    with LOCK, connection() as con:
        account=con.execute("SELECT * FROM account WHERE id=1").fetchone()
        positions=[]; exposure=0; unrealized=0
        for p in con.execute("SELECT * FROM positions ORDER BY opened"):
            p=dict(p); last=prices.get(p["symbol"],{}).get("last")
            p["mark"] = float(last) if last and float(last)>0 else None
            p["market_value"] = p["quantity"]*p["mark"] if p["mark"] else None
            p["unrealized_pnl"] = p["market_value"]-p["cost"] if p["market_value"] is not None else None
            if p["market_value"] is not None:
                exposure+=p["market_value"];unrealized+=p["unrealized_pnl"]
            positions.append(p)
        fills=[dict(x) for x in con.execute("SELECT * FROM fills ORDER BY id DESC LIMIT 30")]
        closed=[x for x in fills if x["side"]=="SELL"]
        equity=account["cash"]+exposure if all(x["mark"] is not None for x in positions) else None
        return {"mode":"PAPER_ONLY","initial_cash":account["initial"],"cash":account["cash"],"equity":equity,"return_pct":(equity/account["initial"]-1)*100 if equity is not None else None,"unrealized_pnl":unrealized,"positions":positions,"fills":fills,"closed_trades":len(closed),"win_rate":100*sum((x["pnl"] or 0)>0 for x in closed)/len(closed) if closed else None,"max_allocation_pct":2,"max_open_positions":MAX_OPEN,"storage":"sqlite", "live_orders_enabled":False}

def order(symbol, side, allocation_pct, stop_loss_pct, take_profit_pct, prices, reason="MANUAL_PAPER"):
    if symbol not in ALLOWED or side not in ("BUY","SELL"):
        raise ValueError("Unsupported symbol or direction")
    if not 0 < allocation_pct <= 2 or not 0.1 <= stop_loss_pct <= 10 or not 0.1 <= take_profit_pct <= 30:
        raise ValueError("Allocation must be 0–2%, stop 0.1–10%, target 0.1–30%")
    price=_positive_price(prices,symbol)
    with LOCK, connection() as con:
        con.execute("BEGIN IMMEDIATE")
        account=con.execute("SELECT * FROM account WHERE id=1").fetchone()
        p=con.execute("SELECT * FROM positions WHERE symbol=?",(symbol,)).fetchone()
        if side=="BUY":
            if p: raise ValueError("Position already open for this symbol")
            if con.execute("SELECT COUNT(*) FROM positions").fetchone()[0]>=MAX_OPEN: raise ValueError("Maximum open positions reached")
            equity=account["cash"]
            for pos in con.execute("SELECT * FROM positions"):
                equity+=_positive_price(prices,pos["symbol"])*pos["quantity"]
            notional=min(equity*allocation_pct/100,account["cash"]/(1+FEE_RATE))
            if notional<1: raise ValueError("Insufficient virtual cash")
            fee=notional*FEE_RATE; qty=notional/price
            con.execute("UPDATE account SET cash=cash-? WHERE id=1",(notional+fee,))
            con.execute("INSERT INTO positions VALUES(?,?,?,?,?,?,?)",(symbol,qty,price,notional+fee,price*(1-stop_loss_pct/100),price*(1+take_profit_pct/100),time.time()))
            pnl=None
        else:
            if not p: raise ValueError("No open position for this symbol")
            qty=p["quantity"];notional=qty*price;fee=notional*FEE_RATE;pnl=notional-fee-p["cost"]
            con.execute("UPDATE account SET cash=cash+? WHERE id=1",(notional-fee,))
            con.execute("DELETE FROM positions WHERE symbol=?",(symbol,))
        con.execute("INSERT INTO fills(symbol,side,quantity,price,fee,pnl,reason,created) VALUES(?,?,?,?,?,?,?,?)",(symbol,side,qty,price,fee,pnl,reason,time.time()))
        con.commit()
    return {"symbol":symbol,"side":side,"quantity":qty,"price":price,"fee":fee,"realized_pnl":pnl,"mode":"PAPER_ONLY"}

def check_stops(prices):
    triggered=[]
    with LOCK, connection() as con:
        rows=[dict(p) for p in con.execute("SELECT * FROM positions")]
    for p in rows:
        quote=prices.get(p["symbol"])
        if not quote:continue
        price=float(quote["last"])
        reason="STOP_LOSS" if price<=p["stop"] else "TAKE_PROFIT" if p["target"] and price>=p["target"] else None
        if reason:
            try: triggered.append(order(p["symbol"],"SELL",2,1,2,prices,reason))
            except ValueError:pass
    return triggered


def performance():
    """Realized, fee-inclusive trade analytics. No fabricated or mark-to-market returns."""
    with LOCK, connection() as con:
        fills=[dict(r) for r in con.execute('SELECT * FROM fills ORDER BY id ASC')]
        cash=con.execute('SELECT cash,initial FROM account WHERE id=1').fetchone()
        positions=[dict(r) for r in con.execute('SELECT symbol,quantity,entry,cost,stop,target FROM positions')]
    closed=[f for f in fills if f['side']=='SELL']
    pnls=[float(f['pnl'] or 0) for f in closed]
    wins=sum(v>0 for v in pnls)
    gross_profit=sum(max(v,0) for v in pnls)
    gross_loss=-sum(min(v,0) for v in pnls)
    curve=[0.0];running=0.0
    for pnl in pnls:
        running+=pnl;curve.append(round(running,6))
    peak=curve[0];max_dd=0.0
    for v in curve:
        peak=max(peak,v);max_dd=max(max_dd,peak-v)
    return {'mode':'PAPER_ONLY','total_orders':len(fills),'completed_round_trips':len(closed),
        'open_positions':len(positions),'realized_pnl_after_fees':round(sum(pnls),4),
        'total_fees':round(sum(float(f['fee']) for f in fills),4),
        'win_rate_pct':round(100*wins/len(closed),2) if closed else None,
        'profit_factor':round(gross_profit/gross_loss,3) if gross_loss else None,
        'realized_drawdown_usd':round(max_dd,4),
        'realized_pnl_curve':curve[-101:], 'cash':cash['cash'],
        'initial_cash':cash['initial'],
        'note':'Realized P&L includes buy/sell fees. Drawdown is based on closed-trade realized P&L only, not intratrade equity.'}
