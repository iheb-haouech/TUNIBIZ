from pathlib import Path
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
url='http://127.0.0.1:8877/'
with sync_playwright() as p:
 try:b=p.chromium.launch(headless=True)
 except Exception:b=p.chromium.launch(channel='msedge',headless=True)
 errors=[]
 page=b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url);page.locator('body.marketing').wait_for();page.locator('.hero-media img').wait_for()
 page.locator('.hero-media img').evaluate('(img)=>img.decode()')
 page.wait_for_timeout(650)
 page.screenshot(path=str(P/'site-preview.png'),full_page=True);page.screenshot(path=str(P/'hero-preview.png'))
 assert 'Un temps d’avance' in page.locator('h1').inner_text()
 for i in range(4):
  page.locator(f'[data-tab="{i}"]').click();assert page.locator(f'[data-tab="{i}"]').get_attribute('aria-pressed')=='true';assert page.locator('#studio .screen').count()==1
 page.locator('.lang').select_option('en');assert 'One step ahead' in page.locator('h1').inner_text()
 page.locator('.lang').select_option('ar');assert page.locator('html').get_attribute('dir')=='rtl'
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'RTL overflow'
 page.screenshot(path=str(P/'arabic-preview.png'))
 page.locator('.lang').select_option('fr')
 page.locator('.hero-copy a.outline').click();page.get_by_role('heading',name='Notre carte').wait_for();assert page.locator('.product').count()>=5
 mobile=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True);mobile.on('pageerror',lambda e:errors.append(str(e)))
 mobile.goto(url);mobile.locator('body.marketing').wait_for();mobile.wait_for_timeout(500)
 assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile overflow'
 mobile.screenshot(path=str(P/'site-mobile-preview.png'),full_page=True)
 mobile.locator('.mobile-menu-toggle').click();assert mobile.locator('.links').is_visible()
 mobile.locator('.links a').first.click();assert not mobile.locator('.links').is_visible()
 mobile.locator('[data-tab="2"]').click();assert mobile.locator('#studio h3').inner_text()=='Une arrivée mieux préparée.'
 mobile.locator('.lang').select_option('ar');assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile RTL overflow'
 mobile.screenshot(path=str(P/'site-mobile-ar-preview.png'),full_page=True)
 assert not errors,errors
 print('PASS desktop + mobile layout, 4 interactive tabs, FR/EN/AR RTL, mobile navigation, working demo link, no JS errors')
 b.close()
