from app import discovery, copy_engine

def test_precompile_addresses_filtered(monkeypatch):
    low='0x'+'0'*39+'1'
    normal='0x'+'a'*40
    monkeypatch.setattr(discovery,'rpc',lambda *a:{'transactions':[{'from':low,'to':normal}]})
    assert discovery.ethereum_candidates()==[normal]

def test_solana_version_one_requested(monkeypatch):
    calls=[]
    def fake(url,method,params):
        calls.append((method,params))
        if method=='getSlot':return 99
        return {'transactions':[]}
    monkeypatch.setattr(discovery,'rpc',fake)
    assert discovery.solana_candidates()==[]
    assert calls[-1][1][1]['maxSupportedTransactionVersion']==1

def test_pool_diagnostics_exist(monkeypatch,tmp_path):
    from app import paper
    monkeypatch.setattr(paper,'DB',tmp_path/'paper.sqlite3')
    copy_engine.record_diagnostics(latest=123,logs=7,valid=2,executed=1,rejected=1,error='')
    d=copy_engine.snapshot()['diagnostics']
    assert d['latest_block']==123 and d['logs_seen']==7 and d['executed']==1
