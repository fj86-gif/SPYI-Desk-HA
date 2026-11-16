"""SPYI Desk for Home Assistant OS.

8099 private Ingress UI: only the Supervisor ingress proxy can request it.
8765 Android API: bearer token required for every endpoint; for Tailscale Serve only.
/data: persistent application data managed by Home Assistant backups.
No Home Assistant or Supervisor API privileges are requested.
"""
from __future__ import annotations
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import spyi_server as market
import spyi_sync_server as sync

DATA=Path(os.environ.get('SPYI_DATA_DIR','/data'))
DATA.mkdir(parents=True,exist_ok=True)
sync.DATA_DIR=DATA
sync.STATE_PATH=DATA/'sync_state.json'
sync.TOKEN_PATH=DATA/'pairing_token.txt'
# State saved atomically; only the app container writes the private directory.
DB=DATA/'spyi_quotes.sqlite3'

INGRESS_PROXY='172.30.32.2' # Supervisor Ingress forwarder, not client-supplied headers.

class IngressHandler(sync.SyncHandler):
    def local_request(self):
        return self.client_address[0]==INGRESS_PROXY or (
            os.environ.get('SPYI_TEST_INGRESS_LOOPBACK')=='1' and
            self.client_address[0] in ('127.0.0.1','::1'))
    def is_authorized(self):return self.local_request()
    def do_OPTIONS(self):
        self.send_error(405)
    def do_GET(self):
        if not self.local_request():
            self.reply({'error':'Only Home Assistant Ingress is allowed'},403);return
        super().do_GET()
    def do_POST(self):
        if not self.local_request():
            self.reply({'error':'Only Home Assistant Ingress is allowed'},403);return
        super().do_POST()
    def do_PUT(self):
        if not self.local_request():
            self.reply({'error':'Only Home Assistant Ingress is allowed'},403);return
        super().do_PUT()

class AndroidHandler(sync.SyncHandler):
    def local_request(self):return False
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/sync/pairing':
            self.reply({'error':'Koppelsleutel uitsluitend via Home Assistant beschikbaar'},403);return
        if not path.startswith('/api/'):
            self.reply({'error':'Not found'},404);return
        if not self.is_authorized():
            self.reply({'error':'Geldige koppelsleutel vereist'},401);return
        super().do_GET()
    def do_POST(self):
        if not self.is_authorized():
            self.reply({'error':'Geldige koppelsleutel vereist'},401);return
        super().do_POST()
    # PUT and OPTIONS in base class already require authorization / checked CORS.


def open_db():
    connection=sqlite3.connect(DB,timeout=5)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('CREATE TABLE IF NOT EXISTS quotes ('
                       'symbol TEXT NOT NULL, as_of TEXT NOT NULL, fetched_at TEXT NOT NULL,'
                       'price REAL NOT NULL, currency TEXT NOT NULL, source TEXT NOT NULL,'
                       'PRIMARY KEY(symbol, as_of))')
    connection.commit()
    return connection


def quote_poller():
    while True:
        try:
            q=market.api_quote('SPYI.DE')
            if q.get('asOf') and q.get('price'):
                with open_db() as db:
                    db.execute('INSERT OR REPLACE INTO quotes VALUES(?,?,?,?,?,?)',(
                        'SPYI.DE',q['asOf'],datetime.now(timezone.utc).isoformat(),
                        float(q['price']),q.get('currency') or 'EUR',q.get('source') or 'Yahoo Finance'))
                    db.commit()
                print('[quotes] SPYI.DE: '+str(q['price'])+' '+str(q['asOf']),flush=True)
            else:
                print('[quotes] No dated quote returned; not persisted',flush=True)
        except Exception as exc:
            print('[quotes] Source unavailable: '+str(exc)[:170],flush=True)
        # Data can be delayed or unavailable. No guarantee of real-time prices.
        time.sleep(900)


def serve(server):
    try: server.serve_forever(poll_interval=0.5)
    finally: server.server_close()


def main():
    sync.token()
    with open_db() as db:pass
    ingress=ThreadingHTTPServer(('0.0.0.0',8099),IngressHandler)
    android=ThreadingHTTPServer(('0.0.0.0',8765),AndroidHandler)
    threading.Thread(target=serve,args=(android,),daemon=True,name='android-api').start()
    threading.Thread(target=quote_poller,daemon=True,name='quote-poller').start()
    print('[spyi] HA Ingress started (8099), Android token API started (8765).',flush=True)
    print('[spyi] All personal data stays in HA persistent /data; do NOT forward ports.',flush=True)
    serve(ingress)

if __name__=='__main__': main()
