from app import discovery

def test_ethereum_addresses(monkeypatch):
    a='0x'+'a'*40
    monkeypatch.setattr(discovery,'rpc',lambda url,m,p:{'transactions':[{'from':a,'to':a},{'from':'invalid','to':None}]})
    assert discovery.ethereum_candidates()==[a]

def test_solana_signers(monkeypatch):
    addr='11111111111111111111111111111111'
    def fake(url,method,params):
        if method=='getSlot':return 100
        return {'transactions':[{'transaction':{'message':{'accountKeys':[{'pubkey':addr,'signer':True},{'pubkey':addr,'signer':False}]}}}]}
    monkeypatch.setattr(discovery,'rpc',fake)
    assert discovery.solana_candidates()==[addr]

def test_snapshot_never_claims_profit(monkeypatch,tmp_path):
    from app import paper
    monkeypatch.setattr(paper,'DB_PATH',str(tmp_path/'paper.sqlite'),raising=False)
    s=discovery.snapshot()
    assert s['verified_profitable_traders']==0
    assert s['paper_copy_execution_enabled'] is False
