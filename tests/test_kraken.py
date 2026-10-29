from fastapi.testclient import TestClient
from app.main import app
from app import kraken

client=TestClient(app)
def test_discovery_does_not_invent_traders():
    d=client.get('/api/discovery').json()
    assert d['verified_traders']==[] and d['selected_traders']==[]
def test_public_market_mock(monkeypatch):
    monkeypatch.setattr(kraken,'prices',lambda:{'BTC/USD':{'last':100.,'bid':99.,'ask':101.,'volume_24h':10.}})
    assert client.get('/api/kraken/markets').json()['markets']['BTC/USD']['last']==100.
def test_unsupported_candles():
    assert client.get('/api/kraken/candles?symbol=BAD').status_code==422
def test_no_live_execution():
    assert client.get('/api/status').json()['live_orders_enabled'] is False
