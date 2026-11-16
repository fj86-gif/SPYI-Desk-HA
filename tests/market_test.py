"""Deterministic tests for real-data contracts. All finance requests mocked."""
import io, tempfile, sys, os, json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
from openpyxl import Workbook

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'spyi_desk'))
from market_store import MarketStore


def check():
    with tempfile.TemporaryDirectory() as td:
        store=MarketStore(Path(td)/'market.sqlite3')
        payload,code=store.response('quote');assert code==503 and 'error' in payload
        assert store.status()['holdings']['ready'] is False
        ts='2026-11-13T16:35:56+00:00'
        with patch('spyi_server.api_quote',return_value={'symbol':'SPYI.DE','price':11.69,'asOf':ts,'currency':'EUR','source':'Yahoo Finance','previousClose':11.80}):
            q=store.update_quote();assert q['price']==11.69
        assert store.response('quote')[0]['asOf']==ts
        with patch('spyi_server.api_quote',side_effect=RuntimeError('429 rate limit')):
            try:store.update_quote()
            except RuntimeError:pass
            else:assert False,'update should fail'
        prev,code=store.response('quote');assert code==200 and prev['price']==11.69 and prev['lastUpdateError']['message'].startswith('429')
        print('PASS stale-but-confirmed quote, source failure preserved')
        for altered in [
            {'symbol':'SPYI.DE','price':11.0,'asOf':ts,'currency':'USD','source':'Wrong Currency'},
            {'symbol':'SPYI.DE','price':11.0,'asOf':'2026-11-12T16:35:56+00:00','currency':'EUR','source':'Older Quote'}
        ]:
            with patch('spyi_server.api_quote',return_value=altered):
                try:store.update_quote()
                except ValueError:pass
                else:assert False,'Unsafe quote was accepted'
        assert store.response('quote')[0]['price']==11.69
        print('PASS wrong-currency and older quotes are never committed')

        points=[{'date':f'2026-10-{i:02d}','close':10+i/100} for i in range(1,30)]
        with patch('spyi_server.api_chart',return_value={'symbol':'SPYI.DE','source':'Yahoo Finance','points':points}):
            store.update_history()
        history,code=store.response('history');assert code==200 and len(history['points'])==29
        print('PASS verified daily market history persisted')
        wb=Workbook();ws=wb.active
        ws.append(['Holdings as of 2026-11-13'])
        ws.append(['Security Name','Ticker','ISIN','Sector','Country','Currency','Weight','Local Price'])
        for i in range(1200):ws.append([f'Company {i}',f'C{i}',f'IE000000{i:04d}', 'Sector','Country','USD',100/1200,20+i/100])
        buff=io.BytesIO();wb.save(buff);xls=buff.getvalue()
        class FakeResponse:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return xls[:size]
        with patch('market_store.urlopen',return_value=FakeResponse()):
            out=store.update_holdings()
        assert out['count']==1200 and 99<out['totalWeight']<101 and out['sourceAsOf']=='2026-11-13'
        cached,code=store.response('holdings');assert code==200 and len(cached['holdings'])==1200
        with patch('market_store.urlopen',side_effect=RuntimeError('unavailable')):
            try:store.update_holdings()
            except RuntimeError:pass
            else: assert False
        cached,code=store.response('holdings');assert code==200 and cached['count']==1200 and cached['lastUpdateError']
        print('PASS official holdings import, validation, durable cache, error retention')
    print('PASS market cache tests')
if __name__=='__main__':check()
