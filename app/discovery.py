"""Public-chain candidate discovery. Activity is NOT trading P&L or proof of profitable traders."""
import os, time, json, urllib.request, re
from . import paper
from .wallets import ETH_RE, SOL_RE
ETH_RPC_DEFAULT='https://ethereum-rpc.publicnode.com'
SOL_RPC_DEFAULT='https://api.mainnet-beta.solana.com'

def rpc(url, method, params):
    request=urllib.request.Request(url,data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Content-Type':'application/json','User-Agent':'LUCAS-V7-public-research'},method='POST')
    with urllib.request.urlopen(request,timeout=15) as response: obj=json.load(response)
    if not isinstance(obj,dict) or obj.get('error') or 'result' not in obj: raise ValueError(str(obj.get('error') if isinstance(obj,dict) else 'Invalid RPC response')[:180])
    return obj['result']

def init():
    with paper.connection() as con:
        con.execute('CREATE TABLE IF NOT EXISTS discovery_candidates(chain TEXT NOT NULL,address TEXT NOT NULL,observations INTEGER NOT NULL,first_seen REAL NOT NULL,last_seen REAL NOT NULL,PRIMARY KEY(chain,address))')
        con.execute('CREATE TABLE IF NOT EXISTS discovery_checks(chain TEXT PRIMARY KEY,checked REAL NOT NULL,state TEXT NOT NULL,detail TEXT NOT NULL)')
        con.commit()

def ethereum_candidates():
    url=os.getenv('ETHEREUM_RPC_URL',ETH_RPC_DEFAULT)
    block=rpc(url,'eth_getBlockByNumber',['latest',True])
    if not isinstance(block,dict):raise ValueError('Ethereum latest block unavailable')
    # Full blocks contain sender/receiver addresses, NOT identified traders or DEX swaps.
    seen=set()
    for tx in block.get('transactions',[])[:250]:
        if isinstance(tx,dict):
            for k in ('from','to'):
                a=tx.get(k)
                if isinstance(a,str) and ETH_RE.fullmatch(a) and int(a,16)>65535:seen.add(a.lower())
    return sorted(seen)[:350]

def solana_candidates():
    url=os.getenv('SOLANA_RPC_URL',SOL_RPC_DEFAULT)
    slot=rpc(url,'getSlot',[{'commitment':'finalized'}])
    # Some mainnet transactions use version 1; request version 1 and retry with
    # version 0 only when a provider does not support that configuration.
    params={'encoding':'jsonParsed','transactionDetails':'full','rewards':False,'maxSupportedTransactionVersion':1}
    try:
        block=rpc(url,'getBlock',[slot,params])
    except ValueError as exc:
        if 'version' not in str(exc).lower(): raise
        params['maxSupportedTransactionVersion']=0
        # Older providers may still reject v1 blocks; report actionable diagnostics.
        block=rpc(url,'getBlock',[slot,params])
    if not isinstance(block,dict):raise ValueError('Solana finalized block unavailable (provider may restrict getBlock)')
    seen=set()
    for tx in block.get('transactions',[])[:120]:
        message=(tx.get('transaction') or {}).get('message') or {}
        for key in message.get('accountKeys',[]):
            if isinstance(key,dict) and key.get('signer') and isinstance(key.get('pubkey'),str) and SOL_RE.fullmatch(key['pubkey']):seen.add(key['pubkey'])
    return sorted(seen)[:200]

def poll():
    init(); output=[]
    for chain,fn in [('ethereum',ethereum_candidates),('solana',solana_candidates)]:
        now=time.time(); state='ok'; detail=''; count=0
        try:
            addresses=fn(); count=len(addresses)
            with paper.connection() as con:
                for address in addresses:
                    con.execute('INSERT INTO discovery_candidates VALUES(?,?,?,?,?) ON CONFLICT(chain,address) DO UPDATE SET observations=observations+1,last_seen=excluded.last_seen',(chain,address,1,now,now))
                con.execute('DELETE FROM discovery_candidates WHERE (chain,address) NOT IN (SELECT chain,address FROM discovery_candidates ORDER BY last_seen DESC LIMIT 3000)')
                con.commit()
        except Exception as exc:state='error';detail=str(exc)[:180]
        with paper.connection() as con:
            con.execute('INSERT INTO discovery_checks VALUES(?,?,?,?) ON CONFLICT(chain) DO UPDATE SET checked=excluded.checked,state=excluded.state,detail=excluded.detail',(chain,now,state,detail));con.commit()
        output.append({'chain':chain,'status':state,'addresses_observed':count,'detail':detail})
    return output

def snapshot():
    init()
    with paper.connection() as con:
        candidates=[dict(x) for x in con.execute('SELECT chain,address,observations,first_seen,last_seen FROM discovery_candidates ORDER BY observations DESC,last_seen DESC LIMIT 30')]
        checks=[dict(x) for x in con.execute('SELECT * FROM discovery_checks ORDER BY chain')]
        total=con.execute('SELECT COUNT(*) FROM discovery_candidates').fetchone()[0]
    return {'status':'OBSERVATION_ONLY','candidates':candidates,'total_candidates':total,'checks':checks,'verified_profitable_traders':0,'copy_signals':0,'paper_copy_execution_enabled':False,'ranking_basis':'Frequency observed in sampled public blocks, not profitability','note':'Observed public addresses are unverified candidates. No P&L, swaps, identity, trader skill, or copy signals are inferred. RPC providers may block high-volume block queries.'}
