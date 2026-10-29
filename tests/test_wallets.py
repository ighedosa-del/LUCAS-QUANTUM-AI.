from app import wallets

def test_empty(monkeypatch):
    monkeypatch.delenv('LUCAS_WATCH_WALLETS',raising=False)
    assert wallets.configured()==[]

def test_validate(monkeypatch):
    monkeypatch.setenv('LUCAS_WATCH_WALLETS','ethereum:0x'+'a'*40+',ethereum:bad,solana:bad')
    assert len(wallets.configured())==1

def test_ethereum_parse(monkeypatch):
    monkeypatch.setattr(wallets,'fetch_json',lambda *a,**k:{'status':'1','result':[{'hash':'0x123','logIndex':'0','value':'1200000','tokenDecimal':'6','timeStamp':'1700000000','tokenSymbol':'USDC','to':'0x'+'a'*40}]})
    e=wallets.eth_events('0x'+'a'*40)
    assert e[0]['quantity']==1.2 and e[0]['direction']=='IN'

def test_solana_parse(monkeypatch):
    monkeypatch.setattr(wallets,'fetch_json',lambda *a,**k:{'result':[{'signature':'abc','blockTime':1700000000,'err':None}]})
    assert wallets.sol_events('a'*40)[0]['kind']=='TRANSACTION_SIGNATURE'
