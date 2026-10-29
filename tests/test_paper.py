from app import paper
import pytest

def test_virtual_buy_sell_and_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(paper,'DB',tmp_path/'paper.sqlite3')
    quotes={'BTC/USD':{'last':50000}}
    initial=paper.snapshot(quotes)
    assert initial['cash']==10000 and initial['live_orders_enabled'] is False
    buy=paper.order('BTC/USD','BUY',2,2,4,quotes)
    assert buy['mode']=='PAPER_ONLY'
    account=paper.snapshot(quotes)
    assert len(account['positions'])==1 and account['cash']<10000
    with pytest.raises(ValueError):paper.order('BTC/USD','BUY',2,2,4,quotes)
    with pytest.raises(ValueError):paper.order('ETH/USD','BUY',2.1,2,4,quotes)
    sold=paper.order('BTC/USD','SELL',2,2,4,{'BTC/USD':{'last':51000}})
    assert sold['realized_pnl'] is not None
    assert paper.snapshot(quotes)['closed_trades']==1

def test_stop_loss(tmp_path,monkeypatch):
    monkeypatch.setattr(paper,'DB',tmp_path/'stops.sqlite3')
    paper.order('BTC/USD','BUY',2,2,4,{'BTC/USD':{'last':50000}})
    out=paper.check_stops({'BTC/USD':{'last':48000}})
    assert out and paper.snapshot({'BTC/USD':{'last':48000}})['positions']==[]
