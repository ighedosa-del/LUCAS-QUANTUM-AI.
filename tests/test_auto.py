from app.auto import decide

def test_no_history():
    assert decide([100]*10)[0]=='WAIT'

def test_flat_market_waits():
    assert decide([100]*30)[0]=='WAIT'

def test_invalid_candle_waits():
    assert decide([100]*25+[float('nan')])[0]=='WAIT'
