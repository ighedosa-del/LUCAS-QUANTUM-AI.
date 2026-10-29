"""Public Kraken market feed. No credentials, orders or trader identity inference."""
import json
import time
from threading import Lock
from urllib.request import Request, urlopen
from urllib.parse import urlencode

PAIRS = {"BTC/USD":"XBTUSD", "ETH/USD":"ETHUSD", "SOL/USD":"SOLUSD", "XRP/USD":"XRPUSD"}
_cache = {}
_lock = Lock()

def public_query(endpoint, params=None):
    url = "https://api.kraken.com/0/public/" + endpoint
    if params:
        url += "?" + urlencode(params)
    request = Request(url, headers={"User-Agent":"LUCAS-Quantum-AI-Paper/1.0", "Accept":"application/json"})
    with urlopen(request, timeout=8) as response:
        data = json.load(response)
    if data.get("error"):
        raise ValueError("Kraken returned an error")
    return data["result"]

def prices():
    with _lock:
        if "prices" in _cache and time.monotonic()-_cache["prices"][0] < 20:
            return _cache["prices"][1]
    result = public_query("Ticker", {"pair": ",".join(PAIRS.values())})
    output = {}
    for symbol, code in PAIRS.items():
        match = next((v for k,v in result.items() if k.upper() in (code, "X"+code.replace("USD", "ZUSD")) or (symbol=="BTC/USD" and k=="XXBTZUSD") or (symbol=="ETH/USD" and k=="XETHZUSD")), None)
        if match is None:
            # Kraken may return canonical pair names; rely on the API's stable result order only as a last resort.
            continue
        output[symbol] = {"last": float(match["c"][0]), "bid":float(match["b"][0]), "ask":float(match["a"][0]), "volume_24h":float(match["v"][1])}
    with _lock:
        _cache["prices"]=(time.monotonic(),output)
    return output

def candles(symbol="BTC/USD", interval=5):
    if symbol not in PAIRS or interval not in (1,5,15,60,240,1440):
        raise ValueError("Unsupported market or interval")
    result=public_query("OHLC", {"pair":PAIRS[symbol],"interval":interval})
    rows=next(v for k,v in result.items() if k!="last")
    return [{"time":int(r[0]),"open":float(r[1]),"high":float(r[2]),"low":float(r[3]),"close":float(r[4]),"volume":float(r[6])} for r in rows[-120:-1]] # exclude unfinished candle
