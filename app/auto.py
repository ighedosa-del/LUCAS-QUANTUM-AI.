"""Autonomous virtual-only Kraken strategy; never submits exchange orders."""
import os, sqlite3, threading, time, math
from . import kraken, paper

INTERVAL_SECONDS = 65
_lock = threading.RLock()
_worker = None

def state_db():
    with paper.connection() as con:
        con.execute("CREATE TABLE IF NOT EXISTS bot_state (id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0, last_bar TEXT NOT NULL DEFAULT '', last_action TEXT NOT NULL DEFAULT 'WAIT', last_reason TEXT NOT NULL DEFAULT 'Not started', updated REAL NOT NULL DEFAULT 0, peak_equity REAL NOT NULL DEFAULT 10000)")
        con.execute("INSERT OR IGNORE INTO bot_state(id,peak_equity) VALUES(1,?)",(paper.STARTING_CASH,))
        con.commit()

def status():
    state_db()
    with paper.connection() as con:
        x=dict(con.execute("SELECT * FROM bot_state WHERE id=1").fetchone())
    return {"running":bool(x['enabled']),"mode":"AUTOMATED_PAPER_ONLY","strategy":"BTC/USD 5m SMA(9/21) crossover with RSI guard","interval_seconds":INTERVAL_SECONDS,"last_action":x['last_action'],"last_reason":x['last_reason'],"last_evaluated":x['updated'],"live_orders_enabled":False}

def set_running(value):
    with _lock:
        state_db()
        with paper.connection() as con:
            con.execute("UPDATE bot_state SET enabled=?, last_reason=? WHERE id=1",(int(value),'Started: waiting for next completed candle' if value else 'Stopped by user'))
            con.commit()
        if value: ensure_worker()
    return status()

def _rsi(closes, length=14):
    changes=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    recent=changes[-length:]
    up=sum(max(d,0) for d in recent)/length
    down=sum(max(-d,0) for d in recent)/length
    return 100 if down==0 else 100-100/(1+up/down)

def decide(closes):
    if len(closes)<23 or not all(math.isfinite(x) and x>0 for x in closes):
        return 'WAIT','Insufficient valid completed candles'
    short_prev=sum(closes[-10:-1])/9
    long_prev=sum(closes[-22:-1])/21
    short_now=sum(closes[-9:])/9
    long_now=sum(closes[-21:])/21
    rsi=_rsi(closes)
    if short_prev<=long_prev and short_now>long_now and rsi<70:
        return 'BUY',f'SMA9 crossed above SMA21; RSI {rsi:.1f}'
    if short_prev>=long_prev and short_now<long_now:
        return 'SELL',f'SMA9 crossed below SMA21; RSI {rsi:.1f}'
    return 'WAIT',f'No qualified crossover; RSI {rsi:.1f}'

def tick():
    with _lock:
        state_db()
        with paper.connection() as con:
            s=dict(con.execute('SELECT * FROM bot_state WHERE id=1').fetchone())
        if not s['enabled']:return
        candles=kraken.candles('BTC/USD',5)
        if not candles:return
        bar=str(candles[-1]['time'])
        if bar==s['last_bar']:return
        prices=kraken.prices()
        if 'BTC/USD' not in prices:raise ValueError('Kraken BTC/USD quote unavailable')
        paper.check_stops(prices)
        account=paper.snapshot(prices)
        equity=account['equity']
        if equity is None:raise ValueError('Cannot value open paper positions')
        peak=max(float(s['peak_equity']),equity)
        drawdown=(equity/peak-1) if peak>0 else 0
        action,reason=decide([float(c['close']) for c in candles])
        # Circuit breaker: halt on a 5% drawdown from the observed paper-equity peak.
        if drawdown<=-0.05:
            action='HALT';reason='5% paper-equity drawdown circuit breaker'; enabled=0
        else:enabled=1
        has_position=any(p['symbol']=='BTC/USD' for p in account['positions'])
        if enabled and ((action=='BUY' and not has_position) or (action=='SELL' and has_position)):
            paper.order('BTC/USD',action,2,2,4,prices,'AUTO_SMA_CROSSOVER')
        elif action in ('BUY','SELL'):
            reason+='; existing position state prevents duplicate trade'
        with paper.connection() as con:
            con.execute('UPDATE bot_state SET enabled=?,last_bar=?,last_action=?,last_reason=?,updated=?,peak_equity=? WHERE id=1',(enabled,bar,action,reason,time.time(),peak))
            con.commit()

def _loop():
    while True:
        try:
            if status()['running']:tick()
        except Exception as exc:
            with paper.connection() as con:
                con.execute('UPDATE bot_state SET last_action=?,last_reason=?,updated=? WHERE id=1',('ERROR',str(exc)[:200],time.time()))
                con.commit()
        time.sleep(INTERVAL_SECONDS)

def ensure_worker():
    global _worker
    if _worker is None or not _worker.is_alive():
        _worker=threading.Thread(target=_loop,daemon=True,name='lucas-paper-bot')
        _worker.start()
