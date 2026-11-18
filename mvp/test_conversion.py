from pathlib import Path
from playwright.sync_api import sync_playwright
import uuid,sqlite3
P=Path(__file__).parent;name='QA lead '+str(uuid.uuid4())[:8]
try:
 with sync_playwright() as p:
  try:b=p.chromium.launch(headless=True)
  except Exception:b=p.chromium.launch(channel='msedge',headless=True)
  page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:8877/');page.locator('#leadform').wait_for()
  assert page.locator('#visits').inner_text()=='4'
  page.locator('#basket').evaluate("(e)=>{e.value=20;e.dispatchEvent(new Event('input'))}")
  assert page.locator('#visits').inner_text()=='3'
  for lang in ['en','ar','fr']:
   page.locator('header select').select_option(lang);page.locator('#leadform').wait_for();assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  for field,val in {'business':name,'contact':'QA','phone':'00000000','city':'Tunis'}.items():page.locator('#leadform input[name='+field+']').fill(val)
  page.locator('#leadform input[name=permission]').check()
  page.locator('#leadform button').click();page.get_by_text('Demande enregistrée dans le prototype local.',exact=True).wait_for()
  with sqlite3.connect(P/'data/tunibiz.sqlite') as c:assert c.execute('SELECT COUNT(*) FROM demo_leads WHERE business=?',(name,)).fetchone()[0]==1
  page.screenshot(path=str(P/'conversion-site-preview.png'),full_page=True)
  mobile=b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  mobile.goto('http://127.0.0.1:8877/');mobile.locator('#leadform').wait_for()
  assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
  mobile.locator('header select').select_option('ar');assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
  assert not errors,errors
  print('PASS conversion page, three languages, local lead stored, calculator, desktop/mobile layout, no JS errors')
  b.close()
finally:
 with sqlite3.connect(P/'data/tunibiz.sqlite') as c:c.execute('DELETE FROM demo_leads WHERE business=?',(name,))
