import sys, os, json, tempfile, threading, time
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from html.parser import HTMLParser
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
    state={'tx':[{'id':'t1','date':'2026-10-26','shares':8,'price':11.63875,'type':'buy','fees':0}], 'holdings':[],'alerts':[],'events':[]}
    status,body,_=request(home,'/api/sync/state',method='PUT',obj={'baseRevision':0,'state':state});assert status==200
    status,body,_=request(external,'/api/sync/state',headers={'Authorization':'Bearer '+token})
    assert json.loads(body)['state']==state
    print('PASS Cross-device write/read persisted')
    assert a.sync.STATE_PATH.exists()
    with a.open_db() as db: assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotes'").fetchone()
    print('PASS SQLite initialized')
finally:
    ingress.shutdown();phone.shutdown();ingress.server_close();phone.server_close();d.cleanup()
