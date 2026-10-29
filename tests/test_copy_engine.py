from app.copy_engine import decode, SWAP_TOPIC

def log(vals):
    return {'topics':[SWAP_TOPIC,'0x'+'0'*64,'0x'+'0'*64], 'data':'0x'+''.join(f'{v:064x}' for v in vals)}

def test_buy_pool_swap():
    assert decode(log([30000000000,0,0,10**19]))==('BUY',10,30000)

def test_sell_pool_swap():
    assert decode(log([0,10**19,30000000000,0]))==('SELL',10,30000)

def test_ambiguous_pool_swap_rejected():
    assert decode(log([1,2,3,4])) is None

def test_not_swap_rejected():
    assert decode({'topics':['0xdeadbeef'],'data':log([1,2,3,4])['data']}) is None


def test_prefix_only_is_not_a_swap():
    bad=log([30000000000,0,0,10**19]);bad['topics'][0]=SWAP_TOPIC[:40]+'0'*26
    assert decode(bad) is None

def test_missing_indexed_topics_rejected():
    bad=log([30000000000,0,0,10**19]);bad['topics']=[SWAP_TOPIC]
    assert decode(bad) is None
