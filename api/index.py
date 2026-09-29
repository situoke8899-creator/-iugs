"""Stateless public market data API. Paper trading is local browser only."""
from fastapi import FastAPI, HTTPException, Query
from urllib.request import Request, urlopen
from urllib.parse import quote
import json, time
app = FastAPI(title="QuantLab Vercel Paper Market API")
CHAINS={"bsc","ethereum","solana"}
def fetch(url):
    try:
        req=Request(url,headers={"User-Agent":"QuantLabPaper/1.0"})
        with urlopen(req,timeout=9) as r: return json.load(r)
    except Exception:
        raise HTTPException(502,"行情提供方暂时不可用，请稍后重试")
@app.get("/api/health")
def health(): return {"ok":True,"mode":"paper","live_trading":False,"background_worker":False}
@app.get("/api/discover")
def discover(chain:str=Query("bsc")):
    if chain not in CHAINS: raise HTTPException(400,"Unsupported chain")
    rows=fetch("https://api.dexscreener.com/token-profiles/latest/v1")
    return [{"chain":chain,"token":r.get("tokenAddress"),"url":r.get("url")} for r in rows if r.get("chainId")==chain and r.get("tokenAddress")][:40]
@app.get("/api/token")
def token(chain:str, address:str):
    if chain not in CHAINS or not 20<=len(address)<=100 or "/" in address: raise HTTPException(400,"Invalid chain/address")
    rows=fetch("https://api.dexscreener.com/token-pairs/v1/"+chain+"/"+quote(address,safe=""))
    pairs=[{"symbol":(r.get("baseToken") or {}).get("symbol"),"name":(r.get("baseToken") or {}).get("name"),"address":(r.get("baseToken") or {}).get("address"),"price":r.get("priceUsd"),"liquidity":(r.get("liquidity") or {}).get("usd"),"volume24":(r.get("volume") or {}).get("h24"),"pair":r.get("pairAddress"),"dex":r.get("dexId"),"created":r.get("pairCreatedAt"),"url":r.get("url")} for r in rows if r.get("priceUsd") and (r.get("liquidity") or {}).get("usd")]
    pairs.sort(key=lambda r:float(r["liquidity"] or 0),reverse=True)
    return {"pairs":pairs[:12],"checked_at":int(time.time())}
@app.get("/api/risk")
def risk(chain:str,address:str):
    if chain not in CHAINS or not 20<=len(address)<=100 or "/" in address: raise HTTPException(400,"Invalid chain/address")
    if chain=="solana":return {"status":"unsupported","pass":False,"warning":"Solana 尚未接入合约安全审计；不可视为安全"}
    cid="56" if chain=="bsc" else "1"
    data=fetch("https://api.gopluslabs.io/api/v1/token_security/"+cid+"?contract_addresses="+quote(address,safe=""))
    info=(data.get("result") or {}).get(address.lower())
    if not info:return {"status":"unknown","pass":False,"warning":"未取得风险报告"}
    flags=["is_honeypot","is_blacklisted","hidden_owner","is_mintable","transfer_pausable","cannot_sell_all"]
    bad=[k for k in flags if str(info.get(k))=="1"]
    unknown=[k for k in flags if str(info.get(k)) not in ("0","1")]
    try: tax_high=float(info["buy_tax"])>.1 or float(info["sell_tax"])>.1
    except (ValueError,TypeError,KeyError):tax_high=True
    return {"status":"screened","pass":not (bad or unknown or tax_high),"bad":bad,"unknown":unknown,"high_or_unknown_tax":tax_high,"warning":"仅初步检查，不能证明安全，也未实际验证可卖出"}
