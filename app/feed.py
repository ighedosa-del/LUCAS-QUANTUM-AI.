"""Fail-closed Kraken quote gate. A successful network response is required for new orders.
Read-only portfolio history remains available during outages.
"""
import math, time, threading
from . import kraken
_lock=threading.RLock()
_state={'status':'unverified','last_success':None,'last_error':None,'failures':0,'last_attempt':None}

def validate(quotes, symbols=()):
    if not isinstance(quotes,dict) or not quotes:
        raise ValueError('Empty Kraken quote response')
    for symbol in symbols:
        q=quotes.get(symbol)
        if not isinstance(q,dict):raise ValueError('Missing Kraken quote: '+symbol)
        for field in ('last','bid','ask'):
            value=float(q[field])
            if not math.isfinite(value) or value<=0 or value>=1e12:
                raise ValueError('Invalid Kraken '+field+' for '+symbol)
    return quotes

def fresh_quotes(symbols=(), retries=2, delay=0.25):
    # Existing Kraken cache is limited to 20 seconds, and never returns stale values after expiration.
    symbols=tuple(symbols)
    last=None
    for attempt in range(retries+1):
        try:
            with _lock:_state['last_attempt']=time.time()
            quotes=validate(kraken.prices(),symbols)
            with _lock:
                _state.update(status='live',last_success=time.time(),last_error=None,failures=0)
            return quotes
        except (OSError,ValueError,KeyError,TypeError,TimeoutError,OverflowError) as exc:
            last=exc
            with _lock:
                _state.update(status='unavailable',last_error=str(exc)[:180],failures=_state['failures']+1)
            if attempt<retries:time.sleep(delay*(2**attempt))
    raise ValueError('Fresh Kraken quotes unavailable; paper orders blocked: '+str(last))

def status():
    with _lock:s=dict(_state)
    s['age_seconds']=round(time.time()-s['last_success'],1) if s['last_success'] else None
    s['orders_allowed']=s['status']=='live' and s['age_seconds'] is not None and s['age_seconds']<=30
    return s
