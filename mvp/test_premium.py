from pathlib import Path
from playwright.sync_api import sync_playwright
P=Path(__file__).parent;url='http://127.0.0.1:8877/'
with sync_playwright() as p:
 try:b=p.chromium.launch(headless=True)
 except Exception:b=p.chromium.launch(channel='msedge',headless=True)
 errors=[]
 page=b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url);page.locator('body.premium').wait_for();assert 'Gérez mieux' in page.locator('h1').inner_text()
 page.evaluate("Promise.all([...document.images].map(i=>i.decode()))")
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 assert page.locator('.psection').count()==5
 assert page.locator('.aud-image').count()==3
 assert page.locator('.solution-item').count()==5
 page.screenshot(path=str(P/'premium-desktop-preview.png'),full_page=True)
 page.screenshot(path=str(P/'premium-hero-preview.png'))
 page.locator('[data-add="0"]').click();assert '3.500 DT' in page.locator('#studio .basket').inner_text()
 page.locator('[data-filter="1"]').click();assert page.locator('#studio .dish').count()==1
 page.locator('[data-filter="-1"]').click();assert page.locator('#studio .dish').count()==3
 page.locator('#studio').screenshot(path=str(P/'premium-product-preview.png'))
 for i in [1,2,3,0]:
  page.locator(f'[data-tab="{i}"]').click();assert page.locator(f'[data-tab="{i}"]').get_attribute('aria-selected')=='true'
 page.locator('.lang').select_option('en');assert 'Manage better' in page.locator('h1').inner_text()
 page.locator('.lang').select_option('ar');assert page.locator('html').get_attribute('dir')=='rtl'
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'RTL overflow'
 page.locator('.lang').select_option('fr')
 page.locator('.hero-copy2 a.outline').click();page.get_by_role('heading',name='Notre carte').wait_for()
 assert page.locator('.product .pic img').count()==3
 assert page.locator('.product .pic svg').count()>=1
 mobile=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True);mobile.on('pageerror',lambda e:errors.append(str(e)))
 mobile.goto(url);mobile.locator('body.premium').wait_for()
 assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile overflow'
 mobile.screenshot(path=str(P/'premium-mobile-preview.png'),full_page=True)
 mobile.screenshot(path=str(P/'premium-mobile-top-preview.png'))
 mobile.locator('.mobile-menu-toggle').click();assert mobile.locator('.links').is_visible()
 mobile.locator('.links a').first.click();assert not mobile.locator('.links').is_visible()
 mobile.locator('[data-tab="2"]').click();assert mobile.locator('#studio .board').count()==1
 mobile.locator('.lang').select_option('ar');assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile RTL overflow'
 assert not errors,errors
 print('PASS homepage structure, all images decoded, preview basket, category filter, 4 product tabs, FR EN AR RTL, desktop & mobile, actual demo menu photos, JS errors 0')
 b.close()
