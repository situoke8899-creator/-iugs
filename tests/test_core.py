import os,tempfile
from backend import core

def setup_function():
 fd,p=tempfile.mkstemp();os.close(fd);core.DB=p;core.init()
def test_init_and_buy_sell():
 assert core.settings()['enabled'] is False
 core.set_settings({'max_exposure_pct':50})
 core.trade('BNB Chain','test','TEST','BUY',25,1,'unit','test',50000)
 assert core.equity()['positions'][0]['qty']>0
 q=core.equity()['positions'][0]['qty']
 core.trade('BNB Chain','test','TEST','SELL',q*1.1,1.1,'unit','test')
 assert not core.equity()['positions']
def test_caps_and_default_disabled():
 assert core.step()['status']=='paused'
 try:core.trade('BNB Chain','x','X','BUY',500,1,'unit','test')
 except ValueError as e:assert 'cap' in str(e)
 else:assert False
