from pathlib import Path
from playwright.sync_api import sync_playwright
import requests, sqlite3, re, datetime, uuid
P=Path(__file__).parent;url='http://127.0.0.1:8877';name='QA Nearby '+str(uuid.uuid4())[:8]
s=requests.Session();h={'X-CSRF-Token':s.get(url+'/api/session').json()['csrf']}
def post(path,d,code=200):
 r=s.post(url+'/api'+path,json=d,headers=h);assert r.status_code==code,(path,r.status_code,r.text);return r.json()
pw=re.search(r'Mot de passe: (.+)',(P/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
assert s.get(url+'/api/nearby/business').status_code==401
post('/login',{'email':'demo@tunibiz.local','password':pw})
with sqlite3.connect(P/'data/tunibiz.sqlite') as c:
 sid=c.execute("SELECT shop_id FROM users WHERE email='demo@tunibiz.local'").fetchone()[0]
 old=c.execute("SELECT lat,lon,address FROM nearby_locations WHERE shop_id=?",(sid,)).fetchone()
oid=None
try:
 post('/nearby/location',{'lat':999,'lon':10,'address':'QA'},400)
 post('/nearby/location',{'lat':33.88,'lon':10.86,'address':'QA fixture'})
 day=datetime.date.today().isoformat()
 oid=post('/nearby/offer',{'title':name,'description':'20% test','starts':day,'ends':day},201)['id']
 data=requests.get(url+'/api/nearby').json()['offers'];assert any(o['id']==oid and o['radius']==1000 for o in data)
 with sync_playwright() as p:
  try:b=p.chromium.launch(headless=True)
  except Exception:b=p.chromium.launch(channel='msedge',headless=True)
  ctx=b.new_context(viewport={'width':390,'height':844},geolocation={'latitude':33.88,'longitude':10.865},permissions=['geolocation'])
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(url);page.locator('.one-price').wait_for();assert '19 DT' in page.locator('.one-price').inner_text();assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  for l in ['en','ar','fr']:
   page.locator('header select').select_option(l);assert '19 DT' in page.locator('.one-price').inner_text();assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  page.goto(url+'/nearby');page.locator('#start').click();page.get_by_role('heading',name=name).wait_for()
  ctx.set_geolocation({'latitude':33.9,'longitude':10.88});page.get_by_role('heading',name=name).wait_for(state='detached')
  page.locator('#stop').click();assert not page.locator('.offer').count()
  assert not errors,errors;b.close()
 post('/nearby/stop',{'id':oid});assert not any(o['id']==oid for o in requests.get(url+'/api/nearby').json()['offers'])
 print('PASS auth, coordinates, promo publication, 1km inclusion/exclusion, stop, 19 DT FR/EN/AR mobile, no JS errors')
finally:
 with sqlite3.connect(P/'data/tunibiz.sqlite') as c:
  if oid:c.execute('DELETE FROM nearby_offers WHERE id=?',(oid,))
  if old:c.execute('UPDATE nearby_locations SET lat=?,lon=?,address=? WHERE shop_id=?',(*old,sid))
  else:c.execute('DELETE FROM nearby_locations WHERE shop_id=?',(sid,))
