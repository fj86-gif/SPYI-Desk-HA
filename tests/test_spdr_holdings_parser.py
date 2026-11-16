"""State Street EMEA parser regression tests using synthetic rows (not real market data)."""
import sys, io, tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'spyi_desk'))
from openpyxl import Workbook
from spyi_server import excel_holdings
from market_store import MarketStore

def fixture(n=6100, fractional=False):
    wb=Workbook();ws=wb.active
    ws.append(['State Street SPDR MSCI ACWI IMI ETF'])
    ws.append(['ISIN IE00B3YLTY66'])
    ws.append(['Holdings As Of:', '2026-11-13'])
    ws.append([]);ws.append([])
    ws.append(['ISIN','SEDOL','Security Name','Currency','Number of Shares',
      'Percent of Fund','Trade Country Name','Local Price',
      'Sector Classification','Industry Classification','Base Market Value'])
    each=(1/n) if fractional else (100/n)
    for i in range(n):
        ws.append([f'US{i:010d}',f'SED{i}',f'Company number {i}','USD',100,
            each,'United States',float(20+i/100),'Information Technology','Software',10000])
    ws.append(['End of report'])
    out=io.BytesIO();wb.save(out);return out.getvalue()

def check():
    for fractional in (False,True):
        rows=excel_holdings(fixture(6100,fractional=fractional))
        assert len(rows)==6100,len(rows)
        assert 99.99<sum(r['weight'] for r in rows)<100.01
        assert rows[0]['name']=='Company number 0'
        assert rows[0]['country']=='United States'
        assert rows[0]['sector']=='Information Technology'
        assert rows[0]['price']==20
        assert rows[0]['isin']=='US0000000000'
        print('PASS SPDR EMEA holdings headers, fractional='+str(fractional))
    with tempfile.TemporaryDirectory() as folder:
        store=MarketStore(Path(folder)/'market.sqlite3')
        with patch('market_store.urlopen',return_value=io.BytesIO(fixture(6100))):
            imported=store.update_holdings()
        assert imported['count']==6100
        result,code=store.response('holdings')
        assert code==200 and result['count']==6100
        assert result['holdings'][0]['sector']=='Information Technology'
        assert store.status()['holdings']['ready']
        print('PASS download -> parse -> validate -> persist -> API')

if __name__=='__main__':check()
