import os,requests,streamlit as st,pandas as pd
st.set_page_config(page_title='QuantLab Pro',layout='wide',page_icon='🧪')
st.title('🧪 QuantLab Pro · 多链模拟交易')
st.error('PAPER ONLY｜不连接钱包，不接受私钥或助记词，不发送真实订单')
url=st.sidebar.text_input('API 地址',os.getenv('QUANT_API_URL','http://127.0.0.1:8000')).rstrip('/')
token=st.sidebar.text_input('管理员访问令牌',type='password',value='')
if not token:st.info('请输入服务端 QUANT_ADMIN_TOKEN 后继续');st.stop()
def req(method,path,**kw):
 try:
  r=requests.request(method,url+path,headers={'Authorization':'Bearer '+token},timeout=25,**kw)
  r.raise_for_status();return r.json()
 except Exception as e:st.error(str(e));return None
s=req('GET','/status')
if s is None:st.stop()
a=s['account'];x,y,z=st.columns(3)
x.metric('虚拟现金',f"${a['cash']:,.2f}");y.metric('估算总资产',f"${a['equity']:,.2f}");z.metric('观察代币',len(s['watch']))
with st.expander('自动轮询设置（仅监控及模拟卖出）'):
 st.warning('自动买入默认关闭：没有跨链完整安全验证前，只生成买入信号，不自动下单。')
 enabled=st.checkbox('启用每分钟扫描（服务器须设置 QUANT_WORKER=1）',value=s['settings']['enabled'])
 if st.button('保存开关'):req('POST','/settings',json={'values':{'enabled':enabled}});st.rerun()
t1,t2,t3,t4=st.tabs(['🔎 新币发现','🛡️ 风险检查','📒 模拟交易','📊 持仓与日志'])
with t1:
 chain=st.selectbox('网络',list(['BNB Chain','Ethereum','Solana']))
 if st.button('查询最新代币简介'):
  found=req('GET','/discover/'+chain)
  if found is not None:st.session_state['found']=found
 if 'found' in st.session_state:
  st.caption('DEX Screener 最近代币简介；并非全链完整新池事件监听。')
  st.dataframe(pd.DataFrame(st.session_state['found']),use_container_width=True)
 with st.form('watch'):
  address=st.text_input('真实代币合约地址 / Mint 地址')
  if st.form_submit_button('加入观察'):
   if req('POST','/watch',json={'chain':chain,'token':address.strip()}):st.success('已加入');st.rerun()
 st.dataframe(pd.DataFrame(s['watch']),use_container_width=True)
with t2:
 chain2=st.selectbox('检测网络',['BNB Chain','Ethereum','Solana'],key='c2')
 token2=st.text_input('待检测合约 / Mint 地址')
 if st.button('查询流动性和合约风险') and token2:
  info=req('GET',f'/inspect/{chain2}/{token2.strip()}')
  if info:st.json(info)
 st.warning('GoPlus 检查仅覆盖此版本的 EVM 网络；Solana 无合约审计验证，默认禁止买入。任何检测结果都不保证代币安全。')
with t3:
 st.caption('使用公开真实报价做虚拟成交，仍不等于真实可成交价格。')
 with st.form('order'):
  oc=st.selectbox('网络',['BNB Chain','Ethereum','Solana'],key='oc')
  ot=st.text_input('代币合约 / Mint 地址',key='ot')
  side=st.selectbox('方向',['BUY','SELL'])
  usd=st.number_input('名义交易金额（USD）',min_value=1.,value=25.)
  if st.form_submit_button('确认虚拟订单'):
   result=req('POST','/paper-order',json={'chain':oc,'token':ot.strip(),'side':side,'usd':usd})
   if result:st.success('虚拟订单已记录');st.json(result)
 if st.button('执行一轮自动扫描'):st.json(req('POST','/step'))
with t4:
 st.subheader('持仓');st.dataframe(pd.DataFrame(a['positions']),use_container_width=True)
 st.subheader('成交');st.dataframe(pd.DataFrame(s['orders']),use_container_width=True)
 st.subheader('系统事件');st.dataframe(pd.DataFrame(s['events']),use_container_width=True)
