"""Capture real setup-mode UI. Start Streamlit on localhost:8501 first."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    kwargs = {'headless':True,'args':['--no-sandbox']}
    if os.getenv('CHROME_PATH'):
        kwargs['executable_path'] = os.environ['CHROME_PATH']
    browser = p.chromium.launch(**kwargs)
    page = browser.new_page(viewport={'width':1500,'height':1260},device_scale_factor=1)
    page.goto('http://localhost:8501',wait_until='networkidle')
    page.get_by_role('heading',name='From satellite scenes to reproducible research').wait_for()
    assert page.get_by_role('button',name='Build map result',exact=True,include_hidden=True).is_disabled()
    page.get_by_label('West',exact=True).wait_for()
    page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden')
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out/'study-design.png'),full_page=True)
    page.get_by_role('tab',name='05 · Methods & catalog').click()
    page.get_by_role('heading',name='Know what each product means').wait_for()
    page.wait_for_timeout(1000)
    page.screenshot(path=str(out/'methods-catalog.png'),full_page=True)
    assert page.locator('[data-testid="stException"]').count() == 0
    browser.close()
    print('Captured actual running UI in unauthenticated setup mode.')
