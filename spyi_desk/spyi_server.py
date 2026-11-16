"""SPYI Desk local data bridge. Python 3.10+, standard library for quotes.
Does not request bank credentials, stores no investment data server-side.
Quote service uses an unofficial Yahoo endpoint and may stop working.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import io
import json
import mimetypes
from pathlib import Path
import re
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse, quote
from urllib.request import Request, urlopen
import webbrowser

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
SOURCE_HTML = ROOT / 'SPYI_Dashboard.html'
MAX_UPLOAD = 16 * 1024 * 1024
CACHE: dict[str,tuple[float,dict]] = {}
LOCK = threading.RLock()
SYMBOL = re.compile(r'^[A-Za-z0-9^=.\-]{1,24}$')
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36'

def yahoo(symbol: str, period='1d', interval='1d') -> dict:
    if not SYMBOL.fullmatch(symbol):
        raise ValueError('Ticker bevat ongeldige tekens')
    if period not in ['1d','5d','1mo','3mo','6mo','1y','2y','5y','max']:
        raise ValueError('Niet ondersteunde periode')
    if interval not in ['1m','2m','5m','15m','30m','60m','1d','1wk','1mo']:
        raise ValueError('Niet ondersteund interval')
    key=f'{symbol}:{period}:{interval}'
    with LOCK:
        cached=CACHE.get(key)
        if cached and time.time()<cached[0]: return cached[1]
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?range={period}&interval={interval}&events=div%2Csplits'
    req = Request(url, headers={'User-Agent': USER_AGENT, 'Accept':'application/json'})
    try:
        with urlopen(req, timeout=11) as resp:
            data=json.loads(resp.read(5_000_000))
    except Exception as e:
        raise RuntimeError(f'Gratis koersbron tijdelijk niet beschikbaar: {str(e)[:180]}')
    results=data.get('chart',{}).get('result') or []
    if not results:
        err=data.get('chart',{}).get('error') or {}
        raise RuntimeError(err.get('description') or 'Geen koersdata voor dit symbool')
    result=results[0]
    with LOCK: CACHE[key]=(time.time()+ (300 if interval in ('1m','5m','15m') else 900), result)
    return result

def api_quote(symbol):
    r=yahoo(symbol, '1d','1d');m=r.get('meta',{})
    p=m.get('regularMarketPrice') or m.get('previousClose') or m.get('chartPreviousClose')
    if not p: raise RuntimeError('Geen geldige koers ontvangen')
    t=m.get('regularMarketTime')
    return {'symbol':symbol,'price':p,'previousClose':m.get('previousClose') or m.get('chartPreviousClose'),
            'high52':m.get('fiftyTwoWeekHigh'),'low52':m.get('fiftyTwoWeekLow'),
            'asOf': datetime.fromtimestamp(t,timezone.utc).isoformat() if t else None,
            'currency':m.get('currency','EUR'),
            'exchange':m.get('exchangeName',''), 'source':'Yahoo Finance (onofficieel)'}

def api_chart(symbol,period,interval):
    r=yahoo(symbol,period,interval)
    timestamps=r.get('timestamp') or []
    data=(r.get('indicators',{}).get('quote') or [{}])[0]
    close=data.get('close') or []
    intraday=interval!='1d'
    points=[]
    for t,v in zip(timestamps,close):
        if not isinstance(v,(float,int)) or v<=0:continue
        d=datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ' if intraday else '%Y-%m-%d')
        points.append({'date':d,'close':round(float(v),6)})
    return {'symbol':symbol,'source':'Yahoo Finance (onofficieel)','points':points}

def excel_holdings(content):
    try: from openpyxl import load_workbook
    except ImportError: raise RuntimeError('Excel-import vereist openpyxl (pip install openpyxl), of gebruik CSV.')
    wb=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
    fields={'name':['security name','name','security description','description','company','security'],
        'ticker':['ticker','symbol','local ticker','ric'],
        'isin':['isin','isin code','security identifier'],
        'sector':['gics sector','sector','sector name'],
        'country':['country','country of risk','country of domicile'],
        'currency':['currency','local currency','ccy'],
        'weight':['weight','weight (%)','weight %','fund weight','portfolio weight','% of fund','weight in fund'],
        'price':['local price','price','market price','last price']}
    def clean(s):return re.sub(r'\s+',' ',str(s or '').strip().lower())
    def get_float(s):
        if isinstance(s,(int,float)):return float(s)
        try:return float(str(s).replace('%','').replace(' ','').replace(',','.'))
        except:return None
    for sheet in wb.worksheets:
        rows=sheet.iter_rows(values_only=True)
        first=[]
        for i,row in enumerate(rows):
            if i>55:break
            h=[clean(v) for v in row]
            if any(k in h for k in fields['name']) and any(k in h for k in fields['weight']):
                first=h
                break
        if not first:continue
        inds={k:next((first.index(label) for label in opts if label in first),-1) for k,opts in fields.items()}
        def v(row,key):
            ix=inds[key]
            return row[ix] if ix>=0 and ix<len(row) else None
        data=[]
        for row in rows:
            name=v(row,'name')
            if not isinstance(name,str) or len(name.strip())<2:continue
            w=get_float(v(row,'weight'))
            if w is None:continue
            p=get_float(v(row,'price'))
            data.append({'name':name.strip(), 'ticker':str(v(row,'ticker') or '').strip(),
             'isin':str(v(row,'isin') or '').strip(), 'sector':str(v(row,'sector') or 'Onbekend').strip(),
             'country':str(v(row,'country') or 'Onbekend').strip(),
             'currency':str(v(row,'currency') or '').strip(),
             'weight':w, 'price':p, 'change':None,'demo':False})
            if len(data)>20000:break
        if data:
            total=sum(x['weight'] for x in data)
            if 0<total<1.5:
                for x in data:x['weight']*=100
            if 1000<total<10000:
                for x in data:x['weight']/=100
            return data
    raise RuntimeError('Geen herkende holdings-tabel. Exporteer de aandelen als CSV met Name, ISIN, Weight.')

def pdf_transactions(content):
    """Deliberately conservative extraction: only accept unambiguous 1-line order data.
    A PDF remains untrusted until the frontend user reviews every detected transaction.
    No brokerage-specific regex is used without a sample statement."""
    try:
        import fitz
        doc=fitz.open(stream=content,filetype='pdf')
        txt='\n'.join(p.get_text(sort=True) for p in doc)
    except ImportError:
        raise RuntimeError('PDF-import vereist pymupdf (pip install pymupdf); gebruik anders CSV.')
    except Exception as e:raise RuntimeError('PDF niet leesbaar: '+str(e))
    if 'IE00B3YLTY66' not in txt.replace(' ','').replace('\n','').upper():
        raise RuntimeError('SPYI-ISIN niet herkend in dit bestand. Geen transacties geïmporteerd.')
    # Without a validated MeDirect template, do NOT guess number of shares and price
    # from arbitrary numbers in the bank statement.
    raise RuntimeError('SPYI herkend, maar de lay-out van dit MeDirect-PDF is nog niet gevalideerd. Gebruik CSV of voeg de transactie handmatig toe. Een voorbeeld-PDF is nodig om deze importer te testen.')

class Handler(BaseHTTPRequestHandler):
    server_version='SPYIDesk/0.3'
    def log_message(self,format,*args): pass
    def reply(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)))
        self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
    def do_GET(self):
        req=urlparse(self.path);q=parse_qs(req.query)
        if req.path in ('/','/SPYI_Dashboard.html'):
            try:b=SOURCE_HTML.read_bytes()
            except FileNotFoundError:self.send_error(404,'Dashboard niet gevonden');return
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b);return
        if not req.path.startswith('/api/'):
            self.send_error(404);return
        try:
            if req.path=='/api/status':out={'ok':True,'service':'SPYI Desk · lokale bridge','version':'v3'}
            elif req.path=='/api/quote':out=api_quote(q.get('symbol',['SPYI.DE'])[0])
            elif req.path=='/api/chart':out=api_chart(q.get('symbol',['SPYI.DE'])[0],q.get('range',['5y'])[0],q.get('interval',['1d'])[0])
            elif req.path=='/api/stocks':
                tickers=q.get('symbols',[''])[0].split(',')
                if len(tickers)>10:raise ValueError('Maximaal 10 tickers per aanvraag')
                out={'quotes':{}}
                for name in tickers:
                    if not SYMBOL.fullmatch(name):continue
                    try:out['quotes'][name]=api_quote(name)
                    except Exception as e:out['quotes'][name]={'error':str(e)}
            else: self.reply({'error':'Onbekend eindpunt'},404);return
            self.reply(out)
        except Exception as e:self.reply({'error':str(e)},503)
    def do_POST(self):
        req=urlparse(self.path)
        if req.path not in ('/api/import/holdings','/api/import/pdf'):
            self.reply({'error':'Niet ondersteund'},404);return
        size=int(self.headers.get('Content-Length','0'))
        if size>MAX_UPLOAD or size<1:
            self.reply({'error':'Bestand te groot of leeg'},413);return
        try:
            # Multipart without a third-party dependency; strict boundary handling.
            typ=self.headers.get('Content-Type','')
            m=re.search(r'boundary=(?:"([^"]+)"|([^;\s]+))',typ)
            if not m:raise ValueError('Uploadformaat niet herkend')
            boundary=(m.group(1) or m.group(2)).encode()
            data=self.rfile.read(size)
            if b'filename=' not in data:raise ValueError('Geen bestand aangeleverd')
            sep=b'\r\n\r\n'
            parts=data.split(b'--'+boundary)
            filedata=None
            for part in parts:
                head,found,body=part.partition(sep)
                if found and b'filename=' in head:filedata=body.rsplit(b'\r\n',1)[0];break
            if filedata is None:raise ValueError('Bestand niet gevonden')
            if req.path.endswith('holdings'):self.reply({'holdings':excel_holdings(filedata)})
            else:self.reply({'transactions':pdf_transactions(filedata)})
        except Exception as e:self.reply({'error':str(e)},400)

if __name__=='__main__':
    p=argparse.ArgumentParser(description='SPYI Desk lokale koersserver')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--no-browser',action='store_true')
    a=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',a.port), Handler)
    url=f'http://127.0.0.1:{a.port}/'
    print('SPYI Desk gestart op',url)
    print('Deze server is alleen bereikbaar op DEZE computer. Stoppen: Ctrl+C.')
    if not a.no_browser:threading.Timer(.55,lambda:webbrowser.open(url)).start()
    try:server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:print('\nSPYI Desk afgesloten.')
    finally:server.server_close()
