"""Persistent market-data cache for SPYI Desk.

All source data is fetched live from third-party endpoints. No generated/demo
prices or holdings are ever returned. A failed update preserves the last
verified snapshot and explicitly reports data freshness / errors.
"""
from __future__ import annotations
import io
import json
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import spyi_server

FUND_ISIN = "IE00B3YLTY66"
SPYI_SYMBOL = "SPYI.DE"
HOLDINGS_URL = "https://www.ssga.com/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spyi-gy.xlsx"
MAX_HOLDINGS_BYTES = 32 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


class MarketStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._initialize()

    def conn(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def _initialize(self):
        with self.conn() as db:
            db.execute("CREATE TABLE IF NOT EXISTS market_snapshot (kind TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS market_errors (kind TEXT PRIMARY KEY, reason TEXT NOT NULL, at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS daily_closes (symbol TEXT NOT NULL, date TEXT NOT NULL, close REAL NOT NULL, PRIMARY KEY (symbol,date))")
            db.commit()

    def snapshot(self, kind):
        with self.conn() as db:
            row = db.execute("SELECT payload,updated_at FROM market_snapshot WHERE kind=?", (kind,)).fetchone()
        if not row:
            return None
        doc = json.loads(row[0])
        doc["fetchedAt"] = row[1]
        return doc

    def error(self, kind):
        with self.conn() as db:
            row = db.execute("SELECT reason,at FROM market_errors WHERE kind=?", (kind,)).fetchone()
        return {"message": row[0], "at": row[1]} if row else None

    def _put(self, kind, data, closes=None):
        fetched = now()
        with self.lock, self.conn() as db:
            db.execute("INSERT OR REPLACE INTO market_snapshot VALUES (?,?,?)", (kind, json.dumps(data, ensure_ascii=False, separators=(',',':')), fetched))
            db.execute("DELETE FROM market_errors WHERE kind=?", (kind,))
            if closes is not None:
                db.executemany("INSERT OR REPLACE INTO daily_closes VALUES (?,?,?)", ((SPYI_SYMBOL, p['date'], p['close']) for p in closes))
            db.commit()
        return fetched

    def _error(self, kind, exc):
        with self.lock, self.conn() as db:
            db.execute("INSERT OR REPLACE INTO market_errors VALUES (?,?,?)", (kind, str(exc)[:400], now()))
            db.commit()

    def update_quote(self):
        try:
            q = spyi_server.api_quote(SPYI_SYMBOL)
            if q.get('symbol') != SPYI_SYMBOL or not isinstance(q.get('price'), (float,int)) or q['price'] <= 0 or not q.get('asOf') or q.get('currency') != 'EUR':
                raise ValueError('Geen gedateerde, geldige SPYI.DE-koers ontvangen')
            timestamp = datetime.fromisoformat(q['asOf'].replace('Z','+00:00'))
            if timestamp.tzinfo is None or timestamp > datetime.now(timezone.utc):
                raise ValueError('Ongeldig tijdstip beurskoers')
            previous=self.snapshot('quote')
            if previous and previous.get('asOf'):
                previous_time=datetime.fromisoformat(previous['asOf'].replace('Z','+00:00'))
                if timestamp<previous_time:
                    raise ValueError('Koersbron leverde een oudere koers dan al opgeslagen')
            q['demo'] = False
            self._put('quote', q)
            return q
        except Exception as exc:
            self._error('quote', exc)
            raise

    def update_history(self):
        try:
            chart = spyi_server.api_chart(SPYI_SYMBOL, 'max','1d')
            points = chart.get('points', [])
            if len(points) < 15:
                raise ValueError('Onvoldoende historische beurskoersen ontvangen')
            points = [{"date": p['date'],"close":float(p['close'])} for p in points
                      if re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(p.get('date','')))
                      and isinstance(p.get('close'),(float,int)) and p['close']>0]
            if len(points)<15:raise ValueError('Historiek bevat te weinig geldige datapunten')
            points=sorted({p['date']:p for p in points}.values(),key=lambda p:p['date'])
            if points[-1]['date']>datetime.now(timezone.utc).date().isoformat():
                raise ValueError('Historische koersbron bevat datums in de toekomst')
            self._put('history', {'symbol': SPYI_SYMBOL,'source':chart.get('source'),'points':points}, closes=points)
            return points
        except Exception as exc:
            self._error('history', exc)
            raise

    @staticmethod
    def parse_source_date(raw):
        """Only return a source date if explicitly present in the published file."""
        try:
            from openpyxl import load_workbook
            wb=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
            for ws in wb.worksheets[:2]:
                for row in ws.iter_rows(max_row=15,max_col=12,values_only=True):
                    for i,v in enumerate(row):
                        if isinstance(v,datetime):
                            # Do not confuse a random report date field with holdings date.
                            if any('as of' in str(x).lower() or 'date' in str(x).lower() for x in row[:i]):
                                return v.date().isoformat()
                        if isinstance(v,str):
                            m=re.search(r'(?:as\s+of|holdings\s+date|data\s+as\s+of)\s*:?\s*(\d{4}-\d{2}-\d{2})',v,re.I)
                            if m:return m.group(1)
        except Exception:
            return None
        return None

    def update_holdings(self):
        try:
            req=Request(HOLDINGS_URL, headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
                                       'Accept':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*',
                                       'Accept-Language':'en-GB,en;q=0.9',
                                       'Referer':'https://www.ssga.com/ie/en_gb/institutional/etfs/state-street-spdr-msci-all-country-world-investable-market-ucits-etf-acc-spyi-gy'})
            with urlopen(req, timeout=45) as resp:
                raw=resp.read(MAX_HOLDINGS_BYTES+1)
            if len(raw)>MAX_HOLDINGS_BYTES or not raw.startswith(b'PK'):
                raise ValueError('State Street leverde geen geldig Excelbestand')
            items=spyi_server.excel_holdings(raw)
            total=sum(float(x.get('weight') or 0) for x in items)
            if len(items)<1000 or not (75<=total<=115):
                raise ValueError(f'Holdings-bestand afgekeurd: {len(items)} posities; totaalgewicht {total:.2f}%')
            doc={'holdings':items,'source':'State Street (officiële dagelijkse holdings)',
                 'sourceUrl':HOLDINGS_URL,'sourceAsOf':self.parse_source_date(raw),
                 'count':len(items),'totalWeight':round(total,6)}
            self._put('holdings',doc)
            return doc
        except Exception as exc:
            self._error('holdings',exc)
            raise

    def import_holdings(self,raw,filename):
        if len(raw)>MAX_HOLDINGS_BYTES:raise ValueError('Bestand groter dan 32 MB')
        if raw.startswith(b'PK'):
            items=spyi_server.excel_holdings(raw)
        else:
            raise ValueError('Gebruik een .xlsx van State Street voor serverimport')
        total=sum(float(x.get('weight') or 0) for x in items)
        if len(items)<1000 or not 75<=total<=115:
            raise ValueError('Bestand bevat geen plausibele volledige SPYI-holdings')
        doc={'holdings':items,'source':'Handmatige import: '+str(filename)[:120],
             'sourceUrl':None,'sourceAsOf':self.parse_source_date(raw),
             'count':len(items),'totalWeight':round(total,6)}
        self._put('holdings',doc)
        return doc

    def response(self,kind):
        payload=self.snapshot(kind)
        if payload is None:
            return {'error':f'Geen geverifieerde {kind}-gegevens beschikbaar', 'sourceError':self.error(kind)},503
        err=self.error(kind)
        if err:payload['lastUpdateError']=err
        return payload,200

    def status(self):
        out={}
        for kind in ('quote','history','holdings'):
            doc=self.snapshot(kind)
            out[kind]={'ready':doc is not None,'fetchedAt':doc.get('fetchedAt') if doc else None,
                       'asOf': doc.get('asOf') or doc.get('sourceAsOf') if doc else None,
                       'source':doc.get('source') if doc else None,'error':self.error(kind)}
            if doc and kind=='holdings':out[kind]['count']=doc.get('count')
        return out
