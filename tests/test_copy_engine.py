from app.copy_engine import decode

def log(vals):
    return {'topics':['0xd78ad95fa46c994b6551d0da85fc275fe613d000000000000000000000000'], 'data':'0x'+''.join(f'{v:064x}' for v in vals)}

def test_buy_pool_swap():
    assert decode(log([30000000000,0,0,10**19]))==('BUY',10,30000)

def test_sell_pool_swap():
    assert decode(log([0,10**19,30000000000,0]))==('SELL',10,30000)

def test_ambiguous_pool_swap_rejected():
    assert decode(log([1,2,3,4])) is None

def test_not_swap_rejected():
    assert decode({'topics':['0xdeadbeef'],'data':log([1,2,3,4])['data']}) is None
