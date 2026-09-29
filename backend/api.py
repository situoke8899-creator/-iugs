import os, threading, time
from fastapi import FastAPI,HTTPException,Header,Depends
from pydantic import BaseModel
from . import core
core.init()
app=FastAPI(title='QuantLab Pro Paper API',version='0.4.0')
TOKEN=os.getenv('QUANT_ADMIN_TOKEN','')
def auth(authorization:str=Header(default='')):
 if not TOKEN or authorization!='Bearer '+TOKEN:raise HTTPException(401,'Set QUANT_ADMIN_TOKEN and supply bearer token')
class Watch(BaseModel):chain:str;token:str
class Order(BaseModel):chain:str;token:str;side:str;usd:float
class Settings(BaseModel):values:dict
def worker():
 while True:
  try:core.step()
  except Exception as e:core.log('worker_error',str(e))
  time.sleep(60)
@app.on_event('startup')
def startup():
 if os.getenv('QUANT_WORKER','0')=='1':threading.Thread(target=worker,daemon=True).start()
@app.get('/health')
def health():return {'status':'ok','mode':'paper_only','signing':False}
@app.get('/status',dependencies=[Depends(auth)])
def status():
 with core.connect() as c:
  return {'settings':core.settings(),'account':core.equity(),'watch':[dict(x) for x in c.execute('SELECT * FROM watch')],
   'orders':[dict(x) for x in c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 100')],
   'events':[dict(x) for x in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 50')]}
@app.post('/settings',dependencies=[Depends(auth)])
def settings(body:Settings):
 try:core.set_settings(body.values);return {'ok':True}
 except ValueError as e:raise HTTPException(400,str(e))
@app.post('/watch',dependencies=[Depends(auth)])
def watch(body:Watch):
 try:core.add_watch(body.chain,body.token);return {'ok':True}
 except ValueError as e:raise HTTPException(400,str(e))
@app.get('/discover/{chain}',dependencies=[Depends(auth)])
def discover(chain:str):
 try:return core.discover(chain)
 except Exception as e:raise HTTPException(502,str(e))
@app.get('/inspect/{chain}/{token}',dependencies=[Depends(auth)])
def inspect(chain:str,token:str):
 try:
  p=core.best_pair(chain,token)
  return {'pair':p,'market':core.risk_pair(p,core.settings()) if p else None,'contract':core.goplus(chain,token)}
 except Exception as e:raise HTTPException(502,str(e))
@app.post('/paper-order',dependencies=[Depends(auth)])
def order(body:Order):
 try:
  p=core.best_pair(body.chain,body.token)
  if not p:raise ValueError('No market pair')
  m=core.risk_pair(p,core.settings())
  if body.side=='BUY':
   if not m['pass_market_filters']:raise ValueError('Market filters failed')
   sec=core.goplus(body.chain,body.token)
   if not sec['pass']:raise ValueError('Contract checks incomplete/failed: no buys')
  return core.trade(body.chain,body.token,(p.get('baseToken') or {}).get('symbol','?'),body.side,body.usd,float(p['priceUsd']),'manual_paper','manual_confirm',m['liquidity'])
 except ValueError as e:raise HTTPException(400,str(e))
@app.post('/step',dependencies=[Depends(auth)])
def step():return core.step()
