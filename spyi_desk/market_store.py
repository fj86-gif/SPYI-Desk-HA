"""Persist verified SPYI prices and State Street fund holdings; never invent data."""
from __future__ import annotations
import io, json, sqlite3, threading, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import spyi_server as source

SYMBOL="SPYI.DE"
HOLDINGS_URL="https://www.ssga.com/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spyi-gy.xlsx"
MAX_SIZE=32*1024*1024

def utc():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with self.db() as d:
            d.execute("CREATE TABLE IF NOT EXISTS snapshots (kind TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)")
            d.execute("CREATE TABLE IF NOT EXISTS failures (kind TEXT PRIMARY KEY, reason TEXT NOT NULL, at TEXT NOT NULL)")
            d.commit()

    def db(self):
        c=sqlite3.connect(self.path,timeout=15)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def get(self,kind):
        with self.db() as d:
            row=d.execute("SELECT payload,fetched_at FROM snapshots WHERE kind=?",(kind,)).fetchone()
            err=d.execute("SELECT reason,at FROM failures WHERE kind=?",(kind,)).fetchone()
        if row:
            result=json.loads(row[0])
            result["fetchedAt"]=row[1]
            if err:result["lastUpdateError"]={"message":err[0],"at":err[1]}
            return result,200
        return {"error":"Geen geverifieerde gegevens beschikbaar","sourceError":{"message":err[0],"at":err[1]} if err else None},503

    def put(self,kind,payload):
        with self.lock,self.db() as d:
            d.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?)",(kind,json.dumps(payload,ensure_ascii=False,separators=(',',':')),utc()))
            d.execute("DELETE FROM failures WHERE kind=?",(kind,))
            d.commit()
        return payload

    def fail(self,kind,error):
        with self.lock,self.db() as d:
            d.execute("INSERT OR REPLACE INTO failures VALUES (?,?,?)",(kind,str(error)[:350],utc()))
            d.commit()

    def guarded(self,kind,fn):
        try:return self.put(kind,fn())
        except Exception as e:
            self.fail(kind,e)
            raise

    def quote(self):
        def fetch():
            q=source.api_quote(SYMBOL)
            if q.get("symbol")!=SYMBOL or not isinstance(q.get("price"),(float,int)) or q["price"]<=0 or not q.get("asOf"):
                raise ValueError("Geen geldige gedateerde SPYI-koers")
            t=datetime.fromisoformat(q["asOf"].replace("Z","+00:00"))
            if t.tzinfo is None or t>datetime.now(timezone.utc):raise ValueError("Ongeldig tijdstip")
            q["demo"]=False
            return q
        return self.guarded("quote",fetch)

    def history(self):
        def fetch():
            doc=source.api_chart(SYMBOL,"5y","1d")
            points=[p for p in doc.get("points",[]) if re.fullmatch(r"\d{4}-\d\d-\d\d",str(p.get("date",""))) and isinstance(p.get("close"),(int,float)) and p["close"]>0]
            if len(points)<15:raise ValueError("Te weinig geverifieerde dagkoersen")
            return {"symbol":SYMBOL,"source":doc.get("source"),"points":points}
        return self.guarded("history",fetch)

    @staticmethod
    def holdings_date(raw):
        try:
            from openpyxl import load_workbook
            book=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
            for ws in book.worksheets[:2]:
                for row in ws.iter_rows(max_row=15,max_col=12,values_only=True):
                    for item in row:
                        if not isinstance(item,str):continue
                        m=re.search(r"(?:as\s+of|holdings\s+date)\s*:?\s*(\d{4}-\d{2}-\d{2})",item,re.I)
                        if m:return m.group(1)
        except Exception:pass
        return None

    def holdings(self):
        def fetch():
            req=Request(HOLDINGS_URL,headers={"User-Agent":"Mozilla/5.0 SPYIDesk/0.6","Accept":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream"})
            with urlopen(req,timeout=45) as resp:raw=resp.read(MAX_SIZE+1)
            if len(raw)>MAX_SIZE or not raw.startswith(b"PK"):raise ValueError("Geen geldig officieel Excelbestand")
            items=source.excel_holdings(raw)
            weight=sum(float(i.get("weight") or 0) for i in items)
            if len(items)<1000 or not 75<=weight<=115:raise ValueError(f"Holdings afgekeurd: {len(items)} posities, {weight:.2f}%")
            return {"holdings":items,"count":len(items),"totalWeight":round(weight,5),
                    "source":"State Street (officiële dagelijkse holdings)",
                    "sourceAsOf":self.holdings_date(raw),"sourceUrl":HOLDINGS_URL}
        return self.guarded("holdings",fetch)

    def status(self):
        result={}
        for kind in ("quote","history","holdings"):
            doc,code=self.get(kind)
            result[kind]={"ready":code==200,"fetchedAt":doc.get("fetchedAt"),"asOf":doc.get("asOf") or doc.get("sourceAsOf"),"source":doc.get("source"),
                          "error":doc.get("lastUpdateError") or doc.get("sourceError")}
            if kind=="holdings" and code==200:result[kind]["count"]=doc.get("count")
        return result
