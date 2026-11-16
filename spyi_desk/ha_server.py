"""Home Assistant ingress + private mobile API for SPYI Desk.
Market values are only verified external records; no demo fallback.
"""
import os,time,threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import spyi_server as market
import spyi_sync_server as sync
from market_store import Store, SYMBOL

DATA=Path(os.environ.get("SPYI_DATA_DIR","/data"))
DATA.mkdir(parents=True,exist_ok=True)
sync.DATA_DIR=DATA
sync.STATE_PATH=DATA/"sync_state.json"
sync.TOKEN_PATH=DATA/"pairing_token.txt"
STORE=Store(DATA/"market.sqlite3")
INGRESS_PROXY="172.30.32.2"

def market_get(handler,path):
    request=urlparse(path)
    query=parse_qs(request.query)
    p=request.path
    if p=="/api/status":
        handler.reply({"ok":True,"service":"SPYI Desk HA","version":"0.6.0","market":STORE.status()});return True
    if p=="/api/data/status":
        handler.reply({"market":STORE.status()});return True
    if p=="/api/holdings":
        data,status=STORE.get("holdings");handler.reply(data,status);return True
    if p=="/api/quote":
        symbol=query.get("symbol",[SYMBOL])[0]
        if symbol==SYMBOL:
            data,status=STORE.get("quote");handler.reply(data,status)
        else:
            try:handler.reply(market.api_quote(symbol))
            except Exception as e:handler.reply({"error":str(e)[:200]},503)
        return True
    if p=="/api/chart":
        symbol=query.get("symbol",[SYMBOL])[0]
        period=query.get("range",["5y"])[0]
        interval=query.get("interval",["1d"])[0]
        if symbol==SYMBOL and period=="5y" and interval=="1d":
            data,status=STORE.get("history");handler.reply(data,status)
        else:
            try:handler.reply(market.api_chart(symbol,period,interval))
            except Exception as e:handler.reply({"error":str(e)[:200]},503)
        return True
    return False

class MarketHandler(sync.SyncHandler):
    def do_GET(self):
        if urlparse(self.path).path in ("/api/status","/api/data/status","/api/holdings","/api/quote","/api/chart"):
            if not self.is_authorized():self.reply({"error":"Authenticatie vereist"},401);return
            if market_get(self,self.path):return
        super().do_GET()

class IngressHandler(MarketHandler):
    def local_request(self):
        return self.client_address[0]==INGRESS_PROXY or (
            os.environ.get("SPYI_TEST_INGRESS_LOOPBACK")=="1" and
            self.client_address[0] in ("127.0.0.1","::1"))
    def is_authorized(self):return self.local_request()
    def do_OPTIONS(self):self.send_error(405)
    def do_GET(self):
        if not self.local_request():self.reply({"error":"Alleen Home Assistant Ingress"},403);return
        super().do_GET()
    def do_POST(self):
        if not self.local_request():self.reply({"error":"Alleen Home Assistant Ingress"},403);return
        super().do_POST()
    def do_PUT(self):
        if not self.local_request():self.reply({"error":"Alleen Home Assistant Ingress"},403);return
        super().do_PUT()

class AndroidHandler(MarketHandler):
    def local_request(self):return False
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/sync/pairing":
            self.reply({"error":"Koppelsleutel uitsluitend via Home Assistant"},403);return
        if not path.startswith("/api/"):
            self.reply({"error":"Niet gevonden"},404);return
        if not self.is_authorized():
            self.reply({"error":"Koppelsleutel vereist"},401);return
        super().do_GET()
    def do_POST(self):
        if not self.is_authorized():self.reply({"error":"Koppelsleutel vereist"},401);return
        super().do_POST()

def poll(name,fn,interval):
    while True:
        try:
            result=fn()
            print("[market] "+name+" updated at "+str(result.get("asOf") or result.get("sourceAsOf") or "downloaded"),flush=True)
        except Exception as exc:
            print("[market] "+name+" unavailable: "+str(exc)[:190],flush=True)
        time.sleep(interval)

def serve(server):
    try:server.serve_forever(poll_interval=0.5)
    finally:server.server_close()

def main():
    sync.token()
    ingress=ThreadingHTTPServer(("0.0.0.0",8099),IngressHandler)
    mobile=ThreadingHTTPServer(("0.0.0.0",8765),AndroidHandler)
    for name,fn,interval in (("quote",STORE.quote,900),("history",STORE.history,43200),("holdings",STORE.holdings,86400)):
        threading.Thread(target=poll,args=(name,fn,interval),daemon=True).start()
    threading.Thread(target=serve,args=(mobile,),daemon=True).start()
    print("[spyi] HA Ingress on 8099; token API on internal 8765; do not forward ports.",flush=True)
    serve(ingress)

if __name__=="__main__":main()
