"""Public Uniswap V2 pool-swap signal -> Kraken ETH/USD PAPER execution.
This is pool-flow following, NOT verified profitable-wallet copy trading.
Solana swap classification and trader ranking remain disabled.
"""
import os, time
from . import paper, kraken
from .discovery import rpc, ETH_RPC_DEFAULT
POOL='0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'  # Uniswap V2 USDC/WETH
SWAP_TOPIC='0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
SWAP_PREFIX=SWAP_TOPIC
DEFAULT_MIN_SWAP_USD=5000.0

def min_swap_usd():
    """Minimum observed USDC side of pool swap. Never disables size filtering."""
    raw=os.getenv('LUCAS_POOL_MIN_SWAP_USD',str(int(DEFAULT_MIN_SWAP_USD)))
    try: amount=float(raw)
    except (TypeError,ValueError): raise ValueError('LUCAS_POOL_MIN_SWAP_USD must be a number between 1000 and 1000000')
    if not (1000<=amount<=1000000) or not __import__('math').isfinite(amount):
        raise ValueError('LUCAS_POOL_MIN_SWAP_USD must be between 1000 and 1000000')
    return amount

def threshold_reason(usd,threshold):
    return f'Pool swap below ${threshold:,.0f} notional threshold' if usd<threshold else None


def init():
    with paper.connection() as c:
        c.execute('CREATE TABLE IF NOT EXISTS copy_state (id INTEGER PRIMARY KEY CHECK(id=1), last_block INTEGER NOT NULL, last_trade REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT \'pending\', detail TEXT NOT NULL DEFAULT \'\')')
        c.execute('CREATE TABLE IF NOT EXISTS copy_signals (tx TEXT NOT NULL, log_index INTEGER NOT NULL, block INTEGER NOT NULL, side TEXT NOT NULL, eth_amount REAL NOT NULL, usdc_amount REAL NOT NULL, decision TEXT NOT NULL, detail TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(tx,log_index))')
        c.execute('CREATE TABLE IF NOT EXISTS copy_diagnostics (id INTEGER PRIMARY KEY CHECK(id=1), latest_block INTEGER, last_scan REAL, logs_seen INTEGER NOT NULL DEFAULT 0, valid_swaps INTEGER NOT NULL DEFAULT 0, executed INTEGER NOT NULL DEFAULT 0, rejected INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT \'\')')
        c.execute('INSERT OR IGNORE INTO copy_diagnostics(id) VALUES(1)')
        cols={r['name'] for r in c.execute('PRAGMA table_info(copy_diagnostics)')}
        for name in ('raw_logs','swap_events','decode_rejected','below_threshold','disabled','risk_rejected','duplicate_events'):
            if name not in cols:c.execute(f'ALTER TABLE copy_diagnostics ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0')
        c.commit()

def record_diagnostics(latest=None,logs=0,valid=0,executed=0,rejected=0,error='',**extra):
    init()
    with paper.connection() as c:
        c.execute('UPDATE copy_diagnostics SET latest_block=COALESCE(?,latest_block),last_scan=?,logs_seen=logs_seen+?,valid_swaps=valid_swaps+?,executed=executed+?,rejected=rejected+?,error=? WHERE id=1',(latest,time.time(),logs,valid,executed,rejected,str(error)[:250]))
        for name,value in extra.items():
            if name in ('raw_logs','swap_events','decode_rejected','below_threshold','disabled','risk_rejected','duplicate_events'):
                c.execute(f'UPDATE copy_diagnostics SET {name}={name}+? WHERE id=1',(int(value),))
        c.commit()

def decode(log):
    topics=log.get('topics') or []
    if len(topics)!=3 or str(topics[0]).lower()!=SWAP_TOPIC:return None
    data=str(log.get('data',''))
    if not data.startswith('0x') or len(data)!=258:return None
    try: a=[int(data[2+i*64:2+(i+1)*64],16) for i in range(4)]
    except ValueError:return None
    # Uniswap V2 USDC token0 (6 decimals), WETH token1 (18 decimals).
    if a[0]>0 and a[3]>0 and a[1]==0 and a[2]==0:side='BUY';usd=a[0]/1e6;eth=a[3]/1e18
    elif a[2]>0 and a[1]>0 and a[0]==0 and a[3]==0:side='SELL';usd=a[2]/1e6;eth=a[1]/1e18
    else:return None
    if not (0<eth<1e7 and 0<usd<1e11):return None
    return side,eth,usd

def poll():
    init()
    url=os.getenv('ETHEREUM_RPC_URL',ETH_RPC_DEFAULT)
    latest=int(rpc(url,'eth_blockNumber',[]),16)
    # Wait for confirmations to reduce reorg-related false signals.
    latest=max(0,latest-3)
    with paper.connection() as c: state=c.execute('SELECT * FROM copy_state WHERE id=1').fetchone()
    if state is None:
        # Never trade old events from before deployment.
        with paper.connection() as c:
            c.execute('INSERT INTO copy_state(id,last_block,status,detail) VALUES(1,?,?,?)',(latest,'primed','Initialized at current block; waiting for new swaps'));c.commit()
        record_diagnostics(latest=latest)
        return {'status':'primed','processed':0,'executed':0}
    start=state['last_block']+1
    if start>latest:
        record_diagnostics(latest=latest)
        return {'status':'up_to_date','processed':0,'executed':0}
    end=min(latest,start+19) # bounded provider load; catch up on subsequent polls
    # Filter by the FULL keccak256 Swap event signature, not all Sync/Mint/Burn logs.
    logs=rpc(url,'eth_getLogs',[{'fromBlock':hex(start),'toBlock':hex(end),'address':POOL,'topics':[SWAP_TOPIC]}])
    if not isinstance(logs,list):raise ValueError('Ethereum log query returned invalid data')
    if len(logs)>250:
        raise ValueError('Provider returned >250 swaps for a bounded block range; refusing to advance cursor and lose signals')
    threshold=min_swap_usd()
    processed=executed=0
    counters={'raw_logs':len(logs),'swap_events':0,'decode_rejected':0,'below_threshold':0,'disabled':0,'risk_rejected':0,'duplicate_events':0}
    for log in logs:
        if str((log.get('topics') or [''])[0]).lower()==SWAP_TOPIC:counters['swap_events']+=1
        parsed=decode(log)
        if not parsed:
            counters['decode_rejected']+=1
            continue
        side,eth,usd=parsed;tx=log.get('transactionHash','');idx=int(log.get('logIndex','0x0'),16)
        with paper.connection() as c:
            if c.execute('SELECT 1 FROM copy_signals WHERE tx=? AND log_index=?',(tx,idx)).fetchone():
                counters['duplicate_events']+=1
                continue
        processed+=1;decision='SKIPPED';detail=''
        # Restrict to substantial, interpretable pool swaps; avoid tiny/noisy trades.
        if usd<threshold:
            detail=threshold_reason(usd,threshold);counters['below_threshold']+=1
        elif os.getenv('LUCAS_POOL_PAPER_COPY','0')!='1':
            detail='Pool-follow paper execution disabled by default';counters['disabled']+=1
        else:
            try:
                quotes=kraken.prices();paper.check_stops(quotes)
                with paper.connection() as c:
                    last=c.execute('SELECT last_trade FROM copy_state WHERE id=1').fetchone()[0]
                if time.time()-last<1800:detail='30-minute paper execution cooldown'
                else:
                    account=paper.snapshot(quotes)
                    if account['equity'] is None or account['equity']<=account['initial_cash']*0.95:detail='5% paper drawdown breaker'
                    else:
                        held=any(p['symbol']=='ETH/USD' for p in account['positions'])
                        if (side=='BUY' and held) or (side=='SELL' and not held):detail='No eligible ETH position change'
                        else:
                            paper.order('ETH/USD',side,1,2,4,quotes,'UNISWAP_POOL_FLOW_PAPER')
                            decision='PAPER_EXECUTED';detail='ETH/USD virtual order from public pool-flow signal'
                            with paper.connection() as c:c.execute('UPDATE copy_state SET last_trade=? WHERE id=1',(time.time(),));c.commit()
                            executed+=1
            except (ValueError,OSError,KeyError,TimeoutError) as exc:detail='Quote or risk check failed: '+str(exc)[:130]
        if decision!='PAPER_EXECUTED' and usd>=threshold and os.getenv('LUCAS_POOL_PAPER_COPY','0')=='1':counters['risk_rejected']+=1
        with paper.connection() as c:
            c.execute('INSERT OR IGNORE INTO copy_signals VALUES(?,?,?,?,?,?,?,?,?)',(tx,idx,int(log.get('blockNumber','0x0'),16),side,eth,usd,decision,detail,time.time()));c.commit()
    with paper.connection() as c:
        c.execute('UPDATE copy_state SET last_block=?,status=?,detail=? WHERE id=1',(end,'ok',f'Processed blocks {start}–{end}'));c.execute('DELETE FROM copy_signals WHERE rowid NOT IN (SELECT rowid FROM copy_signals ORDER BY created DESC LIMIT 500)');c.commit()
    record_diagnostics(latest=latest,logs=len(logs),valid=processed,executed=executed,rejected=processed-executed,**counters)
    return {'status':'ok','processed':processed,'executed':executed,'last_block':end,'lag_blocks':latest-end}

def snapshot():
    init()
    with paper.connection() as c:
        state=c.execute('SELECT * FROM copy_state WHERE id=1').fetchone()
        rows=[dict(x) for x in c.execute('SELECT * FROM copy_signals ORDER BY block DESC,log_index DESC LIMIT 40')]
        diagnostics=dict(c.execute('SELECT * FROM copy_diagnostics WHERE id=1').fetchone())
    return {'strategy':'UNISWAP_V2_USDC_WETH_POOL_FLOW','mode':'PAPER_ONLY','execution_enabled':os.getenv('LUCAS_POOL_PAPER_COPY','0')=='1','minimum_swap_usd':min_swap_usd(),'status':dict(state) if state else {'status':'not_initialized'},'signals':rows,'diagnostics':diagnostics,'verified_lead_traders':0,'solana_copy_enabled':False,'note':'Pool swaps are real public DEX events, not attributable to verified profitable lead traders. ETH/USD paper execution is optional and does not copy an identified wallet. No Solana copy execution.'}
