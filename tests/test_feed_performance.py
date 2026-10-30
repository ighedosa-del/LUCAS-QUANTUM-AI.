import pytest
from app import feed, paper

def test_empty_feed_rejected():
    with pytest.raises(ValueError):feed.validate({},('ETH/USD',))

def test_zero_quote_rejected():
    with pytest.raises(ValueError):feed.validate({'ETH/USD':{'last':0,'bid':10,'ask':10}},('ETH/USD',))

def test_nan_quote_rejected():
    with pytest.raises(ValueError):feed.validate({'ETH/USD':{'last':float('nan'),'bid':10,'ask':10}},('ETH/USD',))

def test_missing_symbol_rejected():
    with pytest.raises(ValueError):feed.validate({'BTC/USD':{'last':1,'bid':1,'ask':1}},('ETH/USD',))

def test_outage_blocks_new_orders(monkeypatch):
    def broken():raise OSError('temporary outage')
    monkeypatch.setattr(feed.kraken,'prices',broken)
    with pytest.raises(ValueError,match='paper orders blocked'):
        feed.fresh_quotes(('ETH/USD',),retries=0)
    assert not feed.status()['orders_allowed']

def test_recovery(monkeypatch):
    monkeypatch.setattr(feed.kraken,'prices',lambda:{'ETH/USD':{'last':2200,'bid':2199,'ask':2201}})
    assert feed.fresh_quotes(('ETH/USD',),retries=0)['ETH/USD']['last']==2200
    assert feed.status()['orders_allowed']

def test_performance_no_trades(monkeypatch,tmp_path):
    monkeypatch.setattr(paper,'DB',tmp_path/'performance.sqlite3')
    p=paper.performance()
    assert p['completed_round_trips']==0 and p['win_rate_pct'] is None

def test_performance_real_fills(monkeypatch,tmp_path):
    monkeypatch.setattr(paper,'DB',tmp_path/'performance.sqlite3')
    q={'ETH/USD':{'last':2000}}
    paper.order('ETH/USD','BUY',1,2,4,q)
    q['ETH/USD']['last']=2050
    paper.order('ETH/USD','SELL',1,2,4,q)
    p=paper.performance()
    assert p['total_orders']==2 and p['completed_round_trips']==1
    assert p['realized_pnl_after_fees']>0 and p['total_fees']>0
