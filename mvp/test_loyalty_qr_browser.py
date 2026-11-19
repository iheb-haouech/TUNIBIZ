"""Isolated browser integration; never touches the running TUNIBIZ database."""
import pathlib, tempfile, shutil, subprocess, sys, os, time, requests, re, uuid
from playwright.sync_api import sync_playwright
P=pathlib.Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=pathlib.Path(tmp)
 for file in ['app.py','crm.py','leads.py','nearby.py','loyalty_qr.py','wallet.py','merchant_dashboard.py','subscriptions.py','google_identity.py','analytics.py','store_scan.py','password_recovery.py']:shutil.copy2(P/file,p/file)
 shutil.copytree(P/'static',p/'static')
 server=subprocess.Popen([sys.executable,'-c',"from app import app;app.run(host='127.0.0.1',port=8879,debug=False)"],cwd=p,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 url='http://127.0.0.1:8879'
 try:
  for i in range(40):
   try:
    if requests.get(url,timeout=.5).ok:break
   except requests.RequestException:time.sleep(.3)
  else:raise AssertionError('Isolated server unavailable')
  pw=re.search(r'Mot de passe: (.+)',(p/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
  s=requests.Session();h={'X-CSRF-Token':s.get(url+'/api/session').json()['csrf']}
  assert s.post(url+'/api/login',json={'email':'demo@tunibiz.local','password':pw},headers=h).ok
  r=s.post(url+'/api/crm/customer',json={'name':'QR Test Client','phone':'','consent':False},headers=h);assert r.status_code==201
  code=r.json()['code'];cid=r.json()['id']
  assert s.post(url+'/api/crm/reward',json={'title':'Cafe offert','cost':200,'description':'Sur place uniquement','visual':'coffee'},headers=h).status_code==201
  assert s.post(url+'/api/crm/reward',json={'title':'Bad','cost':100,'visual':'../x'},headers=h).status_code==400
  assert s.post(url+'/api/crm/purchase',json={'id':cid,'amount':135000,'key':str(uuid.uuid4())},headers=h).status_code==201
  with sync_playwright() as playwright:
   try:browser=playwright.chromium.launch(headless=True)
   except Exception:browser=playwright.chromium.launch(channel='msedge',headless=True)
   client=browser.new_page(viewport={'width':390,'height':844});merchant=browser.new_page()
   errors=[];client.on('pageerror',lambda e:errors.append(str(e)));merchant.on('pageerror',lambda e:errors.append(str(e)))
   client.goto(url+'/loyalty');client.locator('[name=code]').fill(code);client.locator('#login button').click()
   client.locator('.reward-card h3').wait_for()
   assert client.locator('.reward-card h3').inner_text()=='Cafe offert'
   assert client.locator('.reward-card img').get_attribute('src')=='/static/media/espresso.webp'
   assert client.locator('.reward-card progress').get_attribute('value')=='68'
   client.locator('#makeqr').click();client.locator('#qrview canvas').wait_for();token=client.locator('#qrview .code').inner_text();assert token.startswith('TNB1:')
   merchant.goto(url+'/crm');merchant.locator('[name=email]').fill('demo@tunibiz.local');merchant.locator('[name=password]').fill(pw);merchant.locator('#login button').click();merchant.locator('[data-tab=customers]').click();merchant.locator('#resolveqr [name=token]').fill(token);merchant.locator('#resolveqr button').click();merchant.get_by_text('Carte identifiée. Confirmez séparément',exact=False).wait_for()
   assert merchant.get_by_role('heading',name='QR Test Client').count()==1
   assert not errors,errors
   browser.close()
  print('PASS isolated browser: client QR canvas, temporary code, merchant identification, no JS errors')
 finally:server.terminate();server.wait(timeout=10)
