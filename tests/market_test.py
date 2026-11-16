"""Offline regression tests. External services are stubbed, never claimed live."""
import io,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"spyi_desk"))
from market_store import Store

def main():
    with tempfile.TemporaryDirectory() as tmp:
        store=Store(Path(tmp)/"market.sqlite3")
        doc,status=store.get("quote")
        assert status==503
        quote={"symbol":"SPYI.DE","price":11.69,"asOf":"2026-11-13T16:35:56+00:00","currency":"EUR","source":"Yahoo Finance"}
        with patch("spyi_server.api_quote",return_value=quote):
            assert store.quote()["price"]==11.69
        with patch("spyi_server.api_quote",side_effect=RuntimeError("source offline")):
            try:store.quote()
            except RuntimeError:pass
            else:assert False
        old,status=store.get("quote")
        assert status==200 and old["price"]==11.69 and old["lastUpdateError"]
        print("PASS verified cached quote survives source failure")
        history=[{"date":f"2026-10-{i:02d}","close":10+i/100} for i in range(1,30)]
        with patch("spyi_server.api_chart",return_value={"points":history,"source":"Yahoo Finance"}):
            store.history()
        assert len(store.get("history")[0]["points"])==29
        print("PASS historical trading series persisted")
        workbook=Workbook();sheet=workbook.active
        sheet.append(["Holdings as of 2026-11-13"])
        sheet.append(["Security Name","Ticker","ISIN","Sector","Country","Currency","Weight","Local Price"])
        for i in range(1200):
            sheet.append([f"Company {i}",f"C{i}",f"IE000000{i:04d}","Tech","US","USD",100/1200,20.1])
        buf=io.BytesIO();workbook.save(buf);body=buf.getvalue()
        class Dummy:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return body[:size]
        with patch("market_store.urlopen",return_value=Dummy()):
            data=store.holdings()
        assert data["count"]==1200 and 99<data["totalWeight"]<101
        assert data["sourceAsOf"]=="2026-11-13"
        with patch("market_store.urlopen",side_effect=ConnectionError("offline")):
            try:store.holdings()
            except ConnectionError:pass
            else:assert False
        old,status=store.get("holdings")
        assert status==200 and old["count"]==1200 and old["lastUpdateError"]
        print("PASS official holdings validation and outage-safe persistence")
    print("ALL PASS")

if __name__=="__main__":main()
