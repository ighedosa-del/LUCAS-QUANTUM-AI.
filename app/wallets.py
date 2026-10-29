"""Read-only wallet monitor. No private keys, transaction signing or fabricated P&L."""
import os, re, json, time, urllib.request, urllib.parse
from . import paper

ETH_RE=re.compile(r'^0x[a-fA-F0-9]{40}$')
SOL_RE=re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
ETH_API='https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api'
# Routescan is keyless for development. Use SOLANA_RPC_URL for a private provider in production.
SOL_RPC=os.getenv('SOLANA_RPC_URL','https://api.mainnet-beta.solana.com')
MAX_WALLETS=12

def configured():
    raw=os.getenv('LUCAS_WATCH_WALLETS','')
    result=[]
    for item in raw.split(','):
        if not item.strip():continue
        if ':' not in item:continue
        chain,addr=item.strip().split(':',1);chain=chain.strip().lower();addr=addr.strip()
        if (chain=='ethereum' and ETH_RE.fullmatch(addr)) or (chain=='solana' and SOL_RE.fullmatch(addr)):
            if not any(x['chain']==chain and x['address']==addr for x in result):result.append({'chain':chain,'address':addr})
    return result[:MAX_WALLETS]

def fetch_json(url, payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={'User-Agent':'LUCAS-Quantum-AI/6.0','Content-Type':'application/json'},method='POST' if data else 'GET')
    with urllib.request.urlopen(req,timeout=12) as res:
        return json.load(res)

def eth_events(address):
    qs=urllib.parse.urlencode({'module':'account','action':'tokentx','address':address,'page':1,'offset':20,'sort':'desc'})
    obj=fetch_json(ETH_API+'?'+qs)
    if obj.get('status')=='0' and str(obj.get('message','')).lower()=='no transactions found':return []
    if not isinstance(obj.get('result'),list):raise RuntimeError('Ethereum indexer returned no usable transfer data')
    out=[]
    for t in obj['result']:
        if not isinstance(t,dict):continue
        try:
            dec=int(t.get('tokenDecimal',0));quantity=int(t['value'])/(10**dec)
            if not 0<=dec<=36 or not 0<quantity<1e18:continue
            ts=int(t['timeStamp'])
        except (ValueError,KeyError,OverflowError,TypeError):continue
        out.append({'id':str(t.get('hash',''))+':'+str(t.get('logIndex','')),'time':ts,'asset':str(t.get('tokenSymbol','?'))[:30], 'quantity':quantity,'direction':'IN' if t.get('to','').lower()==address.lower() else 'OUT','kind':'ERC20_TRANSFER','tx':str(t.get('hash',''))})
    return out

def sol_events(address):
    obj=fetch_json(SOL_RPC,{'jsonrpc':'2.0','id':1,'method':'getSignaturesForAddress','params':[address,{'limit':20,'commitment':'confirmed'}]})
    if not isinstance(obj.get('result'),list):raise RuntimeError('Solana RPC returned no usable signatures')
    return [{'id':x['signature'],'time':x.get('blockTime'),'asset':'UNKNOWN','quantity':None,'direction':'UNKNOWN','kind':'TRANSACTION_SIGNATURE','tx':x['signature']} for x in obj['result'] if isinstance(x,dict) and x.get('signature') and x.get('err') is None]

def init():
    with paper.connection() as con:
        con.execute("CREATE TABLE IF NOT EXISTS wallet_events (chain TEXT NOT NULL, address TEXT NOT NULL, event_id TEXT NOT NULL, timestamp INTEGER, asset TEXT, quantity REAL, direction TEXT, kind TEXT, tx TEXT, observed REAL NOT NULL, PRIMARY KEY(chain,address,event_id))")
        con.execute("CREATE TABLE IF NOT EXISTS wallet_checks (chain TEXT NOT NULL, address TEXT NOT NULL, checked REAL NOT NULL, state TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', PRIMARY KEY(chain,address))")
        con.commit()

def poll():
    init();result=[]
    for w in configured():
        chain=w['chain'];address=w['address'];now=time.time();state='ok';err='';inserted=0
        try:
            events=eth_events(address) if chain=='ethereum' else sol_events(address)
            with paper.connection() as con:
                for e in events:
                    cur=con.execute('INSERT OR IGNORE INTO wallet_events VALUES(?,?,?,?,?,?,?,?,?,?)',(chain,address,e['id'],e['time'],e['asset'],e['quantity'],e['direction'],e['kind'],e['tx'],now))
                    inserted+=cur.rowcount
                con.execute('DELETE FROM wallet_events WHERE rowid NOT IN (SELECT rowid FROM wallet_events ORDER BY observed DESC LIMIT 1000)')
                con.commit()
        except Exception as ex:
            state='error';err=str(ex)[:180]
        with paper.connection() as con:
            con.execute('INSERT INTO wallet_checks VALUES(?,?,?,?,?) ON CONFLICT(chain,address) DO UPDATE SET checked=excluded.checked,state=excluded.state,error=excluded.error',(chain,address,now,state,err));con.commit()
        result.append({'chain':chain,'address':address,'status':state,'new_events':inserted,'error':err})
    return result

def snapshot():
    init();wallets=configured()
    with paper.connection() as con:
        checks={(x['chain'],x['address']):dict(x) for x in con.execute('SELECT * FROM wallet_checks')}
        events=[dict(x) for x in con.execute('SELECT chain,address,event_id,timestamp,asset,quantity,direction,kind,tx,observed FROM wallet_events ORDER BY observed DESC LIMIT 60')]
    for w in wallets:
        check=checks.get((w['chain'],w['address']),{})
        w.update({'status':check.get('state','pending'),'checked':check.get('checked'),'error':check.get('error','')})
    return {'mode':'READ_ONLY_OBSERVATION','wallets':wallets,'events':events,'observed_events':len(events),'verified_profitable_traders':0,'copy_trading_enabled':False,'note':'Transactions and ERC-20 transfers do not prove profitable trades. Wallet P&L, DEX swap classification and copy orders are not yet verified or enabled. Add watch addresses using LUCAS_WATCH_WALLETS.'}
