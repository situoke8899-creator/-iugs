"""Paper-only execution. No private keys, signing or real orders."""
import os, sqlite3, time, json, threading, requests
from datetime import datetime, timezone
DB=os.getenv('QUANT_DB','quantlab.db')
CHAINS={'BNB Chain':'bsc','Ethereum':'ethereum','Solana':'solana'}
lock=threading.RLock()
def connect():
 c=sqlite3.connect(DB,timeout=30); c.row_factory=sqlite3.Row; c.execute('PRAGMA journal_mode=WAL'); return c
def init():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT);
  CREATE TABLE IF NOT EXISTS watch(id INTEGER PRIMARY KEY,chain TEXT,token TEXT,base TEXT,added INTEGER,UNIQUE(chain,token));
  CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,ts INTEGER,chain TEXT,token TEXT,symbol TEXT,side TEXT,qty REAL,price REAL,fee REAL,strategy TEXT,reason TEXT);
  CREATE TABLE IF NOT EXISTS positions(chain TEXT,token TEXT,symbol TEXT,qty REAL,cost REAL,PRIMARY KEY(chain,token));
  CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts INTEGER,kind TEXT,detail TEXT);
  CREATE TABLE IF NOT EXISTS ticks(chain TEXT,token TEXT,ts INTEGER,price REAL,PRIMARY KEY(chain,token,ts));''')
  for k,v in [('cash','10000'),('enabled','false'),('fee_bps','15'),('slippage_bps','30'),('max_order_usd','100'),('max_positions','5'),('max_exposure_pct','30'),('daily_loss_pct','3'),('stop_loss_pct','8'),('take_profit_pct','15'),('cooldown_sec','3600'),('min_liquidity','50000'),('min_volume24','25000'),('min_age_hours','24'),('max_fdv','100000000'),('buy_rsi','35'),('sell_rsi','70'),('grid_pct','3'),('max_price_impact_pct','2')]:
   c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(k,v))
def settings():
 with connect() as c:return {r['k']:json.loads(r['v']) for r in c.execute('SELECT * FROM settings')}
def set_settings(changes):
 allowed=set(settings())-{'cash'}
 if any(k not in allowed for k in changes):raise ValueError('Unknown or protected setting')
 for k,v in changes.items():
  if k=='enabled':
   if not isinstance(v,bool):raise ValueError('enabled must be boolean')
  elif not isinstance(v,(int,float)) or isinstance(v,bool) or v<0:raise ValueError('Invalid setting')
 with lock,connect() as c:
  for k,v in changes.items():c.execute('UPDATE settings SET v=? WHERE k=?',(json.dumps(v),k))
def log(kind,detail):
 with connect() as c:c.execute('INSERT INTO events(ts,kind,detail) VALUES(?,?,?)',(int(time.time()),kind,str(detail)[:500]))
def http_json(url,params=None):
 r=requests.get(url,params=params,timeout=12,headers={'User-Agent':'QuantLabPaper/1.0'});r.raise_for_status();return r.json()
def discover(chain):
 # DexScreener token profiles are a discovery feed, not exhaustive chain monitoring.
 if chain not in CHAINS:raise ValueError('Unsupported chain')
 data=http_json('https://api.dexscreener.com/token-profiles/latest/v1')
 return [x for x in data if x.get('chainId')==CHAINS[chain] and x.get('tokenAddress')][:40]
def pairs(chain,token):
 if chain not in CHAINS or not token or '/' in token:raise ValueError('Invalid chain/token')
 data=http_json(f'https://api.dexscreener.com/token-pairs/v1/{CHAINS[chain]}/{token}')
 return data if isinstance(data,list) else []
def best_pair(chain,token):
 ps=[p for p in pairs(chain,token) if p.get('priceUsd') and float(p.get('liquidity',{}).get('usd') or 0)>0]
 if not ps:return None
 return max(ps,key=lambda p:float((p.get('liquidity') or {}).get('usd') or 0))
def add_watch(chain,token):
 if chain not in CHAINS or len(token)>100 or not token:raise ValueError('Invalid watch')
 with connect() as c:c.execute('INSERT OR IGNORE INTO watch(chain,token,base,added) VALUES(?,?,?,?)',(chain,token,token,int(time.time())))
def equity(prices=None):
 prices=prices or {};s=settings();total=s['cash'];pos=[]
 with connect() as c:
  for r in c.execute('SELECT * FROM positions WHERE qty>0'):
   p=prices.get((r['chain'],r['token']))
   if p is None:
    t=c.execute('SELECT price FROM ticks WHERE chain=? AND token=? ORDER BY ts DESC LIMIT 1',(r['chain'],r['token'])).fetchone();p=t['price'] if t else r['cost']
   value=r['qty']*p;total+=value;pos.append(dict(r)|{'mark':p,'value':value,'unrealized':value-r['qty']*r['cost']})
 return {'cash':s['cash'],'equity':total,'positions':pos}
def risk_pair(p,s):
 liq=float((p.get('liquidity') or {}).get('usd') or 0)
 vol=float((p.get('volume') or {}).get('h24') or 0)
 fdv=float(p.get('fdv') or 0)
 created=p.get('pairCreatedAt')
 age=(time.time()-created/1000)/3600 if created else None
 reasons=[]
 if liq<s['min_liquidity']:reasons.append('low_liquidity')
 if vol<s['min_volume24']:reasons.append('low_volume')
 if fdv and fdv>s['max_fdv']:reasons.append('high_fdv')
 if age is None or age<s['min_age_hours']:reasons.append('too_new_or_unknown_age')
 if not p.get('priceUsd'):reasons.append('missing_price')
 return {'pass_market_filters':not reasons,'reasons':reasons,'liquidity':liq,'volume24':vol,'fdv':fdv,'age_hours':age,
         'contract_audited':False,'honeypot_verified':False,'sellability_verified':False}
def goplus(chain,token):
 # EVM optional informational screening; fail closed on missing/unavailable results.
 if chain not in ('BNB Chain','Ethereum'):return {'status':'unsupported','pass':False}
 cid='56' if chain=='BNB Chain' else '1'
 try:
  data=http_json(f'https://api.gopluslabs.io/api/v1/token_security/{cid}',{'contract_addresses':token})
  info=(data.get('result') or {}).get(token.lower())
  if not info:return {'status':'no_result','pass':False}
  flags=['is_honeypot','is_blacklisted','can_take_back_ownership','hidden_owner','is_mintable','transfer_pausable','cannot_sell_all']
  unknown=[k for k in flags if str(info.get(k)) not in ('0','1')]
  bad=[k for k in flags if str(info.get(k))=='1']
  buy=info.get('buy_tax');sell=info.get('sell_tax')
  try: high_tax=float(buy)>0.10 or float(sell)>0.10
  except (ValueError,TypeError):high_tax=True
  return {'status':'checked','pass':not (bad or unknown or high_tax),'bad_flags':bad,'unknown_flags':unknown,'high_tax_or_unknown':high_tax,'raw':info}
 except Exception as e:return {'status':'unavailable','pass':False,'error':str(e)[:100]}
def record_tick(chain,token,price,ts=None):
 if price<=0:raise ValueError('Invalid price')
 with connect() as c:c.execute('INSERT OR REPLACE INTO ticks VALUES(?,?,?,?)',(chain,token,int(ts or time.time()),price))
def signal(chain,token,p,s):
 with connect() as c:
  rows=list(c.execute('SELECT ts,price FROM ticks WHERE chain=? AND token=? ORDER BY ts DESC LIMIT 30',(chain,token)))
 prices=[r['price'] for r in reversed(rows)]
 if len(prices)<15:return 'HOLD','insufficient_history'
 diffs=[prices[i]-prices[i-1] for i in range(1,len(prices))]
 ups=sum(max(0,d) for d in diffs[-14:])/14;downs=sum(max(0,-d) for d in diffs[-14:])/14
 rsi=100 if downs==0 else 100-100/(1+ups/downs)
 avg=sum(prices[-15:])/15
 if rsi<=s['buy_rsi'] and prices[-1]<avg:return 'BUY',f'rsi={rsi:.1f}, below_ma'
 if rsi>=s['sell_rsi']:return 'SELL',f'rsi={rsi:.1f}'
 return 'HOLD',f'rsi={rsi:.1f}'
def trade(chain,token,symbol,side,usd,price,strategy,reason,liquidity=0):
 """Paper-only, conservative checks. No network calls, signing or blockchain execution."""
 if side not in ('BUY','SELL') or usd<=0 or price<=0:raise ValueError('Invalid order')
 with lock,connect() as c:
  s=settings(); now=int(time.time());eq=equity();position=next((p for p in eq['positions'] if (p['chain'],p['token'])==(chain,token)),None)
  if side=='BUY':
   if usd>s['max_order_usd']:raise ValueError('Per-order cap')
   if len(eq['positions'])>=s['max_positions'] and not position:raise ValueError('Position cap')
   if sum(p['value'] for p in eq['positions'])+usd>eq['equity']*s['max_exposure_pct']/100:raise ValueError('Exposure cap')
   if liquidity and usd/liquidity*100>s['max_price_impact_pct']:raise ValueError('Liquidity impact cap')
  day=datetime.now(timezone.utc).strftime('%Y-%m-%d')
  daystart=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
  # Conservative daily circuit breaker based on realized net P&L, not full mark-to-market.
  if side=='BUY':
   last=c.execute('SELECT ts FROM orders WHERE chain=? AND token=? ORDER BY ts DESC LIMIT 1',(chain,token)).fetchone()
   if last and now-last['ts']<s['cooldown_sec']:raise ValueError('Cooldown')
  slip=s['slippage_bps']/10000;fee_rate=s['fee_bps']/10000
  exec_price=price*(1+slip if side=='BUY' else 1-slip)
  qty=usd/exec_price;fee=usd*fee_rate
  if side=='BUY':
   if s['cash']<usd+fee:raise ValueError('Insufficient paper cash')
   newcash=s['cash']-usd-fee
   newqty=(position['qty'] if position else 0)+qty
   newcost=((position['qty']*position['cost']) if position else 0)+usd+fee
   newcost/=newqty
  else:
   if not position:raise ValueError('Insufficient paper position')
   qty=min(qty,position['qty'])
   usd=qty*exec_price
   fee=usd*fee_rate
   newcash=s['cash']+usd-fee;newqty=max(0,position['qty']-qty);newcost=position['cost']
  c.execute('UPDATE settings SET v=? WHERE k="cash"',(json.dumps(newcash),))
  c.execute('INSERT OR REPLACE INTO positions VALUES(?,?,?,?,?)',(chain,token,symbol,newqty,newcost))
  c.execute('INSERT INTO orders(ts,chain,token,symbol,side,qty,price,fee,strategy,reason) VALUES(?,?,?,?,?,?,?,?,?,?)',
            (now,chain,token,symbol,side,qty,exec_price,fee,strategy,reason))
  return {'side':side,'qty':qty,'price':exec_price,'fee':fee,'cash':newcash}
def step():
 s=settings()
 if not s['enabled']:return {'status':'paused'}
 results=[]
 with connect() as c:ws=list(c.execute('SELECT * FROM watch'))
 for w in ws:
  chain,token=w['chain'],w['token']
  try:
   p=best_pair(chain,token)
   if not p:results.append({'token':token,'status':'no_pair'});continue
   price=float(p['priceUsd']);record_tick(chain,token,price)
   market=risk_pair(p,s);eq=equity();pos=next((x for x in eq['positions'] if (x['chain'],x['token'])==(chain,token)),None)
   sig,reason=signal(chain,token,p,s)
   # No autonomous purchases until contract checks are integrated per chain.
   if pos and (price<=pos['cost']*(1-s['stop_loss_pct']/100) or price>=pos['cost']*(1+s['take_profit_pct']/100)):
    try:
     out=trade(chain,token,pos['symbol'],'SELL',pos['qty']*price,price,'stop_or_take_profit','price_threshold')
     results.append({'token':token,'status':'sold','order':out})
    except Exception as e:results.append({'token':token,'status':'blocked','reason':str(e)})
   elif sig=='BUY':results.append({'token':token,'status':'buy_signal_only','reason':'contract security not verified; manual paper confirmation required','market':market})
   elif sig=='SELL' and pos:
    try:
     out=trade(chain,token,pos['symbol'],'SELL',pos['qty']*price,price,'rsi',reason)
     results.append({'token':token,'status':'sold','order':out})
    except Exception as e:results.append({'token':token,'status':'blocked','reason':str(e)})
   else:results.append({'token':token,'status':'observed','signal':sig,'reason':reason,'market':market})
  except Exception as e:results.append({'token':token,'status':'error','detail':str(e)[:160]})
 log('step',json.dumps(results)[:500]);return {'status':'completed','results':results}
