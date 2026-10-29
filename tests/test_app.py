from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.core import simulate

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["mode"] == "paper-only"

def test_demo():
    result = client.get("/api/demo")
    assert result.status_code == 200
    assert len(result.json()["backtest"]["equity_curve"]) == 120

def test_webhook_requires_auth():
    body = {"signal_id":"abc", "trader_id":"A", "symbol":"BTC/USD",
            "direction":"BUY","size":0.02,"timestamp":datetime.now(timezone.utc).isoformat()}
    assert client.post("/api/webhook", json=body).status_code == 401

def test_backtest_costs_and_cap():
    r = simulate([100,100,100,100], [
        {"bar":0,"direction":"BUY","size":1},
        {"bar":2,"direction":"SELL","size":0}])
    assert r["closed_trades"] == 1
    assert r["total_return"] < 0
    assert r["total_return"] > -0.001

def test_next_bar_no_lookahead():
    r = simulate([100,100,200], [{"bar":1,"direction":"BUY","size":0.02}])
    assert r["equity_curve"][1] == 10000
