import pytest
from app import copy_engine as c

@pytest.mark.parametrize('value,expected', [('5000',5000),('10000',10000),('25000',25000),('1000',1000)])
def test_valid_threshold(monkeypatch,value,expected):
    monkeypatch.setenv('LUCAS_POOL_MIN_SWAP_USD',value)
    assert c.min_swap_usd()==expected

@pytest.mark.parametrize('value', ['0','999','-10','abc','nan','inf','1000001'])
def test_invalid_threshold(monkeypatch,value):
    monkeypatch.setenv('LUCAS_POOL_MIN_SWAP_USD',value)
    with pytest.raises(ValueError):c.min_swap_usd()

def test_default_threshold(monkeypatch):
    monkeypatch.delenv('LUCAS_POOL_MIN_SWAP_USD',raising=False)
    assert c.min_swap_usd()==5000

def test_threshold_boundary():
    assert c.threshold_reason(4999.99,5000)=='Pool swap below $5,000 notional threshold'
    assert c.threshold_reason(5000,5000) is None
