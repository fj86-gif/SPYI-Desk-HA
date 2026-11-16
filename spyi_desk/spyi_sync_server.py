"""SPYI Desk v4 secure local-first sync API.

Python 3.10+ stdlib. Defaults to loopback only; use Tailscale Serve for private HTTPS.
Zero cloud storage; states are written atomically under ~/.spyi-desk/.
"""
from __future__ import annotations
import argparse
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import webbrowser
from spyi_server import Handler

DATA_DIR = Path.home() / '.spyi-desk'
STATE_PATH = DATA_DIR / 'sync_state.json'
TOKEN_PATH = DATA_DIR / 'pairing_token.txt'
LIMIT = 14 * 1024 * 1024
ORIGIN = 'https://appassets.androidplatform.net'
LOCK = threading.RLock()

def atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with open(temp,'w',encoding='utf-8') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp,path)
    if os.name!='nt': os.chmod(path,0o600)

def token():
    with LOCK:
        if TOKEN_PATH.is_file():
            existing=TOKEN_PATH.read_text(encoding='ascii').strip()
            if len(existing)>=32: return existing
        result=secrets.token_urlsafe(32)
        atomic_write(TOKEN_PATH,result+'\n')
        return result

def read_doc():
    if not STATE_PATH.exists(): return {'revision':0,'state':None,'updatedAt':None}
    with open(STATE_PATH,'r',encoding='utf-8') as f:doc=json.load(f)
    # Migration from v0.5: discard market/demo fields, preserve actual user input.
    if isinstance(doc.get('state'),dict):
        permitted=('tx','alerts','events','monthlyPlan','goal','ticker','refreshMinutes','sim')
        doc['state']={k:v for k,v in doc['state'].items() if k in permitted}
    return doc

def validate(state):
    if not isinstance(state,dict): raise ValueError('Ongeldige staat')
    for k in ('tx','alerts','events'):
        if not isinstance(state.get(k),list): raise ValueError(f'Veld {k} moet een lijst zijn')
    for t in state['tx']:
        if not isinstance(t,dict) or not isinstance(t.get('id'),str) or len(t['id'])>160:
            raise ValueError('Ongeldige transactie')
    for forbidden in ('quote','history','holdings','intraday'):
        if forbidden in state: raise ValueError('Marktgegevens horen niet in privésynchronisatie')
    # Prevent recursive/prototype-pollution-shaped payloads from becoming client state.
    def check(obj,depth=0):
        if depth>15:raise ValueError('Gegevensstructuur te diep')
        if isinstance(obj,dict):
            if len(obj)>100:raise ValueError('Te veel eigenschappen')
            if any(k in ('__proto__','prototype','constructor') for k in obj):raise ValueError('Verboden veldnaam')
            for v in obj.values():check(v,depth+1)
        elif isinstance(obj,list):
            if len(obj)>25000:raise ValueError('Te veel regels')
            for v in obj:check(v,depth+1)
    check(state)

def apply_update(base_revision,state):
    validate(state)
    with LOCK:
        doc=read_doc()
        if doc['revision'] != base_revision: return False,doc
        new={'revision':doc['revision']+1,'state':state,'updatedAt':datetime.now(timezone.utc).isoformat()}
        atomic_write(STATE_PATH,json.dumps(new,ensure_ascii=False,separators=(',',':')))
        return True,new

class SyncHandler(Handler):
    server_version='SPYIDeskSync/0.4'
    def local_request(self):
        # Tailscale Serve forwards HTTPS via loopback; the external Host header is retained.
        host=self.headers.get('Host','').split(':')[0].lower()
        origin=self.headers.get('Origin','')
        return (self.client_address[0] in ('127.0.0.1','::1')
                and host in ('127.0.0.1','localhost')
                and self.headers.get('Sec-Fetch-Site','') == 'same-origin'
                and not self.headers.get('Tailscale-User-Login')
                and origin in ('','http://127.0.0.1:8765','http://localhost:8765'))
    def is_authorized(self):
        if self.local_request():return True
        supplied=self.headers.get('Authorization','')
        return supplied.startswith('Bearer ') and hmac.compare_digest(supplied[7:],token())
    def reply(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'none'")
        if self.headers.get('Origin')==ORIGIN:
            self.send_header('Access-Control-Allow-Origin',ORIGIN)
            self.send_header('Vary','Origin')
        self.send_header('Content-Length',str(len(b)))
        self.end_headers();self.wfile.write(b)
    def do_OPTIONS(self):
        if self.headers.get('Origin')!=ORIGIN or not self.path.startswith('/api/'):
            self.send_error(403);return
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin',ORIGIN)
        self.send_header('Access-Control-Allow-Methods','GET, PUT, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type')
        self.send_header('Access-Control-Max-Age','600')
        self.send_header('Vary','Origin')
        self.end_headers()
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/sync/pairing':
            if not self.local_request():self.reply({'error':'Koppelcode alleen op Windows zichtbaar'},403)
            else:self.reply({'token':token(),'message':'Voer deze sleutel uitsluitend op je eigen telefoon in.'})
            return
        if p=='/api/sync/state':
            if not self.is_authorized():self.reply({'error':'Koppelsleutel ontbreekt of is ongeldig'},401);return
            with LOCK:
                doc=read_doc()
                since=parse_qs(urlparse(self.path).query).get('since',[''])[0]
                if since==str(doc['revision']):
                    self.reply({'revision':doc['revision'],'unchanged':True,'updatedAt':doc['updatedAt']})
                else:self.reply(doc)
            return
        if p.startswith('/api/') and not self.is_authorized():
            self.reply({'error':'Onbevoegd apparaat'},401);return
        super().do_GET()
    def do_POST(self):
        if not self.is_authorized():self.reply({'error':'Onbevoegd apparaat'},401);return
        super().do_POST()
    def do_PUT(self):
        if urlparse(self.path).path!='/api/sync/state':self.reply({'error':'Niet gevonden'},404);return
        if not self.is_authorized():self.reply({'error':'Onbevoegd apparaat'},401);return
        if 'application/json' not in self.headers.get('Content-Type',''):
            self.reply({'error':'JSON vereist'},415);return
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:size=0
        if size<1 or size>LIMIT:self.reply({'error':'Gegevens zijn te groot of leeg'},413);return
        try:
            data=json.loads(self.rfile.read(size))
            base=data.get('baseRevision')
            if not isinstance(base,int) or isinstance(base,bool) or base<0:raise ValueError('baseRevision ontbreekt')
            ok,doc=apply_update(base,data.get('state'))
            if not ok:self.reply({'error':'conflict','revision':doc['revision'],'state':doc['state'],'updatedAt':doc['updatedAt']},409)
            else:self.reply({'ok':True,'revision':doc['revision'],'updatedAt':doc['updatedAt']})
        except (ValueError,TypeError,RecursionError) as e:self.reply({'error':str(e)},400)

if __name__=='__main__':
    p=argparse.ArgumentParser(description='SPYI Desk v4 — lokale koers- en synchronisatieserver')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--no-browser',action='store_true')
    args=p.parse_args()
    token()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),SyncHandler)
    url=f'http://127.0.0.1:{args.port}/'
    print('SPYI Desk v4 draait op',url)
    print('Gegevens:',str(DATA_DIR))
    print('De server luistert ALLEEN op localhost. Gebruik Tailscale Serve voor een beveiligde telefoonverbinding.')
    if not args.no_browser:threading.Timer(.6,lambda:webbrowser.open(url)).start()
    try:server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:pass
    finally:server.server_close()
