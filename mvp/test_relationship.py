from pathlib import Path
from playwright.sync_api import sync_playwright
import re, sqlite3, uuid
P=Path(__file__).parent;url='http://127.0.0.1:8877'
name='QA browser '+str(uuid.uuid4())[:8]
try:
 with sync_playwright() as p:
  try:b=p.chromium.launch(headless=True)
  except Exception:b=p.chromium.launch(channel='msedge',headless=True)
  errors=[]; page=b.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(url);page.locator('h1').wait_for();assert 'Des clients qui reviennent' in page.locator('h1').inner_text()
  page.locator('img').first.evaluate('(i)=>i.decode()');page.screenshot(path=str(P/'crm-home-preview.png'))
  page.locator('select').select_option('ar');assert page.locator('html').get_attribute('dir')=='rtl';assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  page.locator('select').select_option('en');assert 'Customers who return' in page.locator('h1').inner_text()
  page.locator('select').select_option('fr')
  page.locator('header a[href="/crm"]').click();page.locator('input[name=password]').fill(re.search(r'Mot de passe: (.+)',(P/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip())
  page.get_by_role('button',name='Se connecter').click();page.get_by_role('heading',name='Votre relation client.').wait_for()
  page.locator('#create input[name=name]').fill(name);page.locator('#create input[name=consent]').check();page.get_by_role('button',name='Créer la carte').click()
  code=page.locator('.code').inner_text();assert len(code)>20
  page.locator('.item').filter(has_text=name).get_by_role('button',name='Voir').click()
  page.locator('#purchase input[name=amount]').fill('12.500');page.get_by_role('button',name='Créditer les points').click();page.get_by_text('Achat enregistré',exact=True).wait_for()
  page.screenshot(path=str(P/'crm-business-preview.png'))
  mobile=b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);mobile.on('pageerror',lambda e:errors.append(str(e)))
  mobile.goto(url);mobile.locator('h1').wait_for();assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
  mobile.screenshot(path=str(P/'crm-mobile-home-preview.png'))
  mobile.goto(url+'/loyalty');mobile.locator('input[name=code]').fill(code);mobile.get_by_role('button',name='Se connecter').click();mobile.get_by_text('12',exact=False).first.wait_for();assert '12' in mobile.locator('.card h2').inner_text()
  mobile.screenshot(path=str(P/'loyalty-mobile-preview.png'),full_page=True);assert not errors,errors
  print('PASS desktop + mobile CRM homepage FR/EN/AR, merchant login, card creation, purchase and private mobile loyalty card; no JS errors',flush=True)
  b.close()
finally:
 with sqlite3.connect(P/'data/tunibiz.sqlite') as c:
  ids=c.execute('SELECT id FROM crm_customers WHERE name=?',(name,)).fetchall()
  for (i,) in ids:c.execute('DELETE FROM loyalty_ledger WHERE customer_id=?',(i,));c.execute('DELETE FROM crm_customers WHERE id=?',(i,))
