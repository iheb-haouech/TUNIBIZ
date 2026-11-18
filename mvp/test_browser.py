from pathlib import Path
from playwright.sync_api import sync_playwright
import re
P=Path(__file__).parent
pw=re.search(r'Mot de passe: (.+)',(P/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
with sync_playwright() as p:
 try:b=p.chromium.launch(headless=True)
 except Exception:b=p.chromium.launch(channel='msedge',headless=True)
 page=b.new_page(viewport={'width':1440,'height':1000})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8877/');page.locator('h1').wait_for();page.screenshot(path=str(P/'site-preview.png'),full_page=True)
 page.goto('http://127.0.0.1:8877/business');page.locator('input[name=password]').fill(pw);page.get_by_role('button',name='Se connecter').click();page.get_by_role('heading',name='Commandes reçues').wait_for()
 page.screenshot(path=str(P/'business-preview.png'),full_page=True)
 page.get_by_role('button',name='Catalogue',exact=True).click();page.get_by_role('heading',name='Ajouter un produit').wait_for()
 mobile=b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
 mobile.on('pageerror',lambda e:errors.append(str(e)))
 mobile.goto('http://127.0.0.1:8877/menu/demo');mobile.get_by_role('heading',name='Notre carte').wait_for();mobile.get_by_role('button',name='+',exact=True).first.click()
 assert mobile.locator('#basket').inner_text().startswith('1 article')
 assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'),'mobile overflow'
 mobile.screenshot(path=str(P/'mobile-preview.png'),full_page=True)
 assert not errors,errors
 print('PASS browser desktop landing, merchant login and catalog, mobile menu and cart; no JS errors')
 b.close()
