"""Nearby end-to-end tests on an isolated server; no real user coordinates or tile provider calls."""
from pathlib import Path
import tempfile,shutil,subprocess,sys,time,requests,re,datetime
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for name in ['app.py','crm.py','leads.py','nearby.py','loyalty_qr.py','wallet.py','merchant_dashboard.py','subscriptions.py','google_identity.py','analytics.py','password_recovery.py']:shutil.copy2(P/name,p/name)
 shutil.copytree(P/'static',p/'static')
 server=subprocess.Popen([sys.executable,'-c',"from app import app;app.run(host='127.0.0.1',port=8879,debug=False)"],cwd=p,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 url='http://127.0.0.1:8879'
 try:
  for _ in range(40):
   try:
    if requests.get(url,timeout=.5).ok:break
   except requests.RequestException:time.sleep(.25)
  else:raise AssertionError('Test server unavailable')
  pw=re.search(r'Mot de passe: (.+)',(p/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
  s=requests.Session();h={'X-CSRF-Token':s.get(url+'/api/session').json()['csrf']}
  assert s.post(url+'/api/login',json={'email':'demo@tunibiz.local','password':pw},headers=h).ok
  assert s.post(url+'/api/nearby/location',json={'lat':33.88,'lon':10.86,'address':'Test fixture'},headers=h).ok
  day=datetime.date.today().isoformat()
  for title,category in [('QA Coffee','coffee'),('QA Food','restaurant')]:
   r=s.post(url+'/api/nearby/offer',json={'title':title,'description':'QA conditions','starts':day,'ends':day,'category':category},headers=h);assert r.status_code==201,r.text
  r=s.post(url+'/api/nearby/offer',json={'title':'Invalid','description':'QA','starts':day,'ends':day,'category':'../x'},headers=h)
  assert r.status_code==400,r.text
  with sync_playwright() as w:
   try:b=w.chromium.launch(headless=True)
   except Exception:b=w.chromium.launch(channel='msedge',headless=True)
   ctx=b.new_context(viewport={'width':390,'height':844},geolocation={'latitude':33.88,'longitude':10.865,'accuracy':50},permissions=['geolocation'])
   page=ctx.new_page();errors=[];external=[];api_calls=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('request',lambda r:api_calls.append((r.method,r.url,r.post_data)) if '/api/' in r.url else None)
   ctx.route('https://tile.openstreetmap.org/**',lambda r:(external.append(r.request.url),r.fulfill(status=204)))
   page.goto(url+'/nearby');page.locator('#start').click();page.get_by_role('heading',name='QA Coffee').wait_for()
   assert page.locator('#nearby-map .offer-marker').count()==1 # grouped at same coordinates
   assert not external
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
   page.locator('[data-category=coffee]').click();assert page.get_by_role('heading',name='QA Food').count()==0
   page.locator('.offer-marker').click();page.locator('#offer-detail').wait_for(state='visible');assert 'QA Coffee' in page.locator('#offer-detail').inner_text()
   page.locator('#close-detail').click()
   page.locator('.leaflet-control-zoom-in').click();page.locator('#recenter').click()
   page.once('dialog',lambda d:d.dismiss());page.locator('#map-toggle').click();assert not external
   page.once('dialog',lambda d:d.accept());page.locator('#map-toggle').click();page.wait_for_timeout(500);assert external,'No map tile requests after consent'
   page.locator('#map-toggle').click();page.wait_for_timeout(100)
   ctx.set_geolocation({'latitude':33.90,'longitude':10.88,'accuracy':50});page.get_by_role('heading',name='QA Coffee').wait_for(state='detached')
   page.locator('#stop').click();assert page.locator('#map-panel').is_hidden()
   assert all(method=='GET' and body is None and '?' not in url_ for method,url_,body in api_calls),api_calls
   assert not errors,errors
   b.close()
  print('PASS Nearby categories, grouped markers, details, zoom/recenter, 1km boundary, privacy and tile consent; no actual external tile calls')
 finally:server.terminate();server.wait(timeout=10)
