import sys, os, json, tempfile, threading, time
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from html.parser import HTMLParser
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]/'spyi_desk'
sys.path.insert(0,str(root))
d=tempfile.TemporaryDirectory()
os.environ['SPYI_DATA_DIR']=d.name
os.environ['SPYI_TEST_INGRESS_LOOPBACK']='1'
import ha_server as a

def start(cls):
    s=ThreadingHTTPServer(('127.0.0.1',0),cls)
    threading.Thread(target=s.serve_forever,daemon=True).start()
    return s, f'http://127.0.0.1:{s.server_port}'
ingress,home=start(a.IngressHandler)
phone,external=start(a.AndroidHandler)
def request(base,path,method='GET',obj=None,headers=None):
    body=None
    if obj is not None:
        body=json.dumps(obj).encode()
        headers={'Content-Type':'application/json',**(headers or {})}
    req=Request(base+path,data=body,method=method,headers=headers or {})
    try:
        with urlopen(req,timeout=3) as r:return r.status,r.read(),dict(r.headers)
    except HTTPError as e:return e.code,e.read(),dict(e.headers)
try:
    status,body,head=request(home,'/')
    assert status==200 and b'SPYI Desk' in body,(status,body[:200]);print('PASS ingress dashboard HTML')
    status,body,_=request(home,'/api/status');assert status==200 and json.loads(body)['ok'];print('PASS ingress authenticated bridge')
    status,body,_=request(home,'/api/sync/pairing');assert status==200
    token=json.loads(body)['token'];assert len(token)>32;print('PASS Ingress pairing code')
    status,body,_=request(external,'/');assert status==404;print('PASS Android front-end denied')
    status,body,_=request(external,'/api/sync/pairing');assert status==403;print('PASS Android pairing denied')
    status,body,_=request(external,'/api/sync/state');assert status==401;print('PASS Anonymous mobile state denied')
    status,body,_=request(external,'/api/status');assert status==401;print('PASS Anonymous mobile market denied')
    status,body,_=request(external,'/api/sync/state',headers={'Authorization':'Bearer bad'});assert status==401
    status,body,_=request(external,'/api/sync/state',headers={'Authorization':'Bearer '+token});assert status==200 and json.loads(body)['revision']==0
    print('PASS Mobile access control')
    state={'tx':[{'id':'t1','date':'2020-01-02','shares':2,'price':10.0,'type':'buy','fees':0}], 'alerts':[],'events':[]}
    status,body,_=request(home,'/api/sync/state',method='PUT',obj={'baseRevision':0,'state':state});assert status==200
    status,body,_=request(external,'/api/sync/state',headers={'Authorization':'Bearer '+token})
    assert json.loads(body)['state']==state
    print('PASS Cross-device write/read persisted')
    invalid_examples=[
      {'tx':[{'id':'x','date':'2999-01-01','type':'buy','shares':1,'price':1.0,'fees':0.0}],'alerts':[],'events':[]},
      {'tx':[{'id':'x','date':'2020-01-02','type':'sell','shares':1,'price':1.0,'fees':0.0}],'alerts':[],'events':[]},
      {'tx':[{'id':'x','date':'2020-01-02','type':'buy','shares':1,'price':-1.0,'fees':0.0}],'alerts':[],'events':[]},
      {'tx':[{'id':'x','date':'2020-01-02','type':'buy','shares':1,'price':1.0,'fees':0.0},
             {'id':'x','date':'2020-01-03','type':'buy','shares':1,'price':1.0,'fees':0.0}],'alerts':[],'events':[]}
    ]
    for invalid in invalid_examples:
        status,body,_=request(home,'/api/sync/state',method='PUT',obj={'baseRevision':1,'state':invalid})
        assert status==400, (status,body)
    status,body,_=request(home,'/api/sync/state')
    assert status==200 and json.loads(body)['revision']==1
    print('PASS server rejects invalid transactions without corrupting synced state')

    assert a.sync.STATE_PATH.exists()
    with a.STORE.conn() as db: assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_snapshot'").fetchone()
    print('PASS SQLite initialized')
    status,body,_=request(external,'/api/holdings/refresh',method='POST',obj={})
    assert status==401, (status,body)
    print('PASS unauthorized mobile cannot trigger provider download')
    with patch.object(a.STORE,'update_holdings',return_value={'count':6000}) as fake:
        status,body,_=request(home,'/api/holdings/refresh',method='POST',obj={})
        assert status==202 and json.loads(body)['started'], (status,body)
        for _ in range(30):
            if fake.called and not a._HOLDINGS_REFRESH_LOCK.locked():break
            time.sleep(.02)
        assert fake.called
        status,body,_=request(home,'/api/holdings/refresh',method='POST',obj={})
        assert status==429 and json.loads(body).get('retryAfterSeconds',0)>0
        print('PASS ingress holdings refresh and cooldown')
    status,body,_=request(home,'/api/data/status')
    assert status==200 and 'holdingsRefreshRunning' in json.loads(body)
    print('PASS holdings status diagnostics')
finally:
    ingress.shutdown();phone.shutdown();ingress.server_close();phone.server_close();d.cleanup()
