"""Browser test with no network sources; exercises no-placeholder data contract."""
import os, tempfile, time, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
    env={**os.environ,'SPYI_DATA_DIR':temp,'SPYI_TEST_INGRESS_LOOPBACK':'1'}
    server=subprocess.Popen([sys.executable,'-u',str(root/'spyi_desk'/'ha_server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        time.sleep(1)
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1280,'height':900})
            errs=[]
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.goto('http://127.0.0.1:8099/',wait_until='domcontentloaded')
            page.wait_for_timeout(1500)
            print('page_title',page.title())
            print('dataBadge',page.locator('#dataBadge').inner_text())
            print('oPrice',page.locator('#oPrice').inner_text())
            print('holdCount',page.locator('#holdCount').inner_text())
            print('pageerrors',errs)
            assert 'GEEN KOERS' in page.locator('#dataBadge').inner_text()
            assert '—' in page.locator('#oPrice').inner_text(), page.locator('#oPrice').inner_text()
            assert not errs,errs
            page.screenshot(path='/mnt/data/spyi_beta_real_data_empty.png',full_page=True)
            browser.close()
    finally:
        server.terminate();server.wait(timeout=10)
