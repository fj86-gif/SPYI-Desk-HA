"""SPYI Desk on HA OS: authenticated Ingress UI and token-protected mobile API.
All market data is verified, cached on disk, and explicitly dated.
"""
from __future__ import annotations
import json
import os
import threading
import time
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs

import spyi_server as market
import spyi_sync_server as sync
from market_store import MarketStore, SPYI_SYMBOL

DATA=Path(os.environ.get('SPYI_DATA_DIR','/data'))
DATA.mkdir(parents=True,exist_ok=True)
sync.DATA_DIR=DATA
sync.STATE_PATH=DATA/'sync_state.json'
sync.TOKEN_PATH=DATA/'pairing_token.txt'
STORE=MarketStore(DATA/'market.sqlite3')
INGRESS_PROXY='172.30.32.2'
_HOLDINGS_REFRESH_LOCK=threading.Lock()
_HOLDINGS_REFRESH_AT=0.0

def request_holdings_refresh():
    """Run a manual retry in the background, limited to once per minute."""
    global _HOLDINGS_REFRESH_AT
    if not _HOLDINGS_REFRESH_LOCK.acquire(blocking=False):
        return {'started':False,'running':True},202
    remaining=60-(time.monotonic()-_HOLDINGS_REFRESH_AT)
    if _HOLDINGS_REFRESH_AT and remaining>0:
        _HOLDINGS_REFRESH_LOCK.release()
        return {'started':False,'error':'Wacht even voor een nieuwe importpoging','retryAfterSeconds':round(remaining)},429
    _HOLDINGS_REFRESH_AT=time.monotonic()
    def task():
        try:
            result=STORE.update_holdings()
            print('[market] manual holdings refreshed '+str(result.get('count')),flush=True)
        except Exception as exc:
            print('[market] manual holdings failed: '+str(exc)[:230],flush=True)
        finally:
            _HOLDINGS_REFRESH_LOCK.release()
    threading.Thread(target=task,daemon=True,name='holdings-manual-refresh').start()
    return {'started':True,'running':True},202



def market_get(handler,path):
    """Handled by both ingress and token-protected mobile API."""
    route=urlparse(path)
    query=parse_qs(route.query)
    if route.path=='/api/status':
        handler.reply({'ok':True,'service':'SPYI Desk · HA','version':'0.6.3','market':STORE.status()});return True
    if route.path=='/api/quote':
        symbol=query.get('symbol',[SPYI_SYMBOL])[0]
        if symbol==SPYI_SYMBOL:
            data,code=STORE.response('quote');handler.reply(data,code)
        else:
            try:handler.reply(market.api_quote(symbol))
            except Exception as e:handler.reply({'error':str(e)[:250]},503)
        return True
    if route.path=='/api/chart':
        symbol=query.get('symbol',[SPYI_SYMBOL])[0]
        period=query.get('range',['5y'])[0];interval=query.get('interval',['1d'])[0]
        if symbol==SPYI_SYMBOL and interval=='1d' and period in ('5y','max'):
            data,code=STORE.response('history');handler.reply(data,code)
        else:
            try:handler.reply(market.api_chart(symbol,period,interval))
            except Exception as e:handler.reply({'error':str(e)[:250]},503)
        return True
    if route.path=='/api/holdings':
        data,code=STORE.response('holdings');handler.reply(data,code);return True
    if route.path=='/api/stocks':
        symbols=[s.strip() for s in query.get('symbols',[''])[0].split(',') if s.strip()]
        if len(symbols)>10:handler.reply({'error':'Maximaal 10 aandelen per aanvraag'},400);return True
        out={'quotes':{}}
        for symbol in symbols:
            if not market.SYMBOL.fullmatch(symbol):continue
            try:out['quotes'][symbol]=market.api_quote(symbol)
            except Exception as e:out['quotes'][symbol]={'error':str(e)[:180]}
        handler.reply(out);return True
    if route.path=='/api/data/status':
        handler.reply({'market':STORE.status(),'holdingsRefreshRunning':_HOLDINGS_REFRESH_LOCK.locked()});return True
    return False


class MarketHandler(sync.SyncHandler):
    def do_GET(self):
        route=urlparse(self.path).path
        if route in ('/api/status','/api/quote','/api/chart','/api/holdings','/api/data/status','/api/stocks'):
            if not self.is_authorized():
                self.reply({'error':'Authenticatie vereist'},401);return
            if market_get(self,self.path):return
        super().do_GET()


class IngressHandler(MarketHandler):
    def local_request(self):
        return self.client_address[0]==INGRESS_PROXY or (
            os.environ.get('SPYI_TEST_INGRESS_LOOPBACK')=='1' and
            self.client_address[0] in ('127.0.0.1','::1'))
    def is_authorized(self):return self.local_request()
    def do_OPTIONS(self):self.send_error(405)
    def do_GET(self):
        if not self.local_request():self.reply({'error':'Alleen Home Assistant Ingress'},403);return
        super().do_GET()
    def do_POST(self):
        if not self.local_request():self.reply({'error':'Alleen Home Assistant Ingress'},403);return
        if urlparse(self.path).path=='/api/holdings/refresh':
            data,status=request_holdings_refresh();self.reply(data,status);return
        super().do_POST()
    def do_PUT(self):
        if not self.local_request():self.reply({'error':'Alleen Home Assistant Ingress'},403);return
        super().do_PUT()


class AndroidHandler(MarketHandler):
    def local_request(self):return False
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/sync/pairing':
            self.reply({'error':'Koppelsleutel uitsluitend via Home Assistant beschikbaar'},403);return
        if not path.startswith('/api/'):
            self.reply({'error':'Niet gevonden'},404);return
        if not self.is_authorized():
            self.reply({'error':'Geldige koppelsleutel vereist'},401);return
        super().do_GET()
    def do_POST(self):
        if not self.is_authorized():self.reply({'error':'Geldige koppelsleutel vereist'},401);return
        super().do_POST()


def one_job(name, fn, period_seconds):
    """Fail closed: failed fetches do not replace verified snapshots."""
    while True:
        try:
            result=fn()
            size=len(result) if isinstance(result,list) else result.get('count','') if isinstance(result,dict) else ''
            print('[market] '+name+' updated '+str(size), flush=True)
            wait_seconds=period_seconds
        except Exception as exc:
            print('[market] '+name+' unavailable: '+str(exc)[:230],flush=True)
            wait_seconds=1800 if name=='holdings' else period_seconds
        time.sleep(wait_seconds)


def serve(server):
    try:server.serve_forever(poll_interval=.5)
    finally:server.server_close()


def main():
    sync.token()
    ingress=ThreadingHTTPServer(('0.0.0.0',8099),IngressHandler)
    android=ThreadingHTTPServer(('0.0.0.0',8765),AndroidHandler)
    for name,fun,delay in [('quote',STORE.update_quote,900),('history',STORE.update_history,12*3600),('holdings',STORE.update_holdings,24*3600)]:
        threading.Thread(target=one_job,args=(name,fun,delay),name=name+'-poller',daemon=True).start()
    threading.Thread(target=serve,args=(android,),daemon=True,name='android-api').start()
    print('[spyi] Ingress (8099) & token-protected mobile API (8765) started.',flush=True)
    print('[spyi] Quote: Yahoo unofficieel, holdings: State Street, errors shown; NEVER forward 8765.',flush=True)
    serve(ingress)

if __name__=='__main__':main()
