"""Registration/admin browser checks with isolated test database."""
import tempfile,os,subprocess,sys,time,requests,shutil
from pathlib import Path
from werkzeug.security import generate_password_hash
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for n in ['app.py','crm.py','leads.py','nearby.py','loyalty_qr.py','wallet.py','merchant_dashboard.py','subscriptions.py','google_identity.py','analytics.py']:shutil.copy2(P/n,p/n)
 shutil.copytree(P/'static',p/'static')
 env={**os.environ,'TUNIBIZ_ADMIN_PASSWORD_HASH':generate_password_hash('QA-admin-passphrase')}
 server=subprocess.Popen([sys.executable,'-c',"from app import app;app.run(host='127.0.0.1',port=8879,debug=False)"],cwd=p,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 url='http://127.0.0.1:8879'
 try:
  for _ in range(40):
   try:
    if requests.get(url,timeout=.5).ok:break
   except requests.RequestException:time.sleep(.3)
  else:raise AssertionError('Server unavailable')
  with sync_playwright() as w:
   try:b=w.chromium.launch(headless=True)
   except Exception:b=w.chromium.launch(channel='msedge',headless=True)
   ctx=b.new_context(viewport={'width':390,'height':844});page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(url+'/merchant-register')
   for name,value in {'name':'QA New Shop','city':'Midoun','address':'Test fixture','lat':'33.88','lon':'10.86','email':'qa-shop@example.test','password':'QA-shop-passphrase'}.items():page.locator('[name='+name+']').fill(value)
   page.locator('[name=confirmed]').check();page.locator('button[type=submit]').click()
   page.get_by_text('Demande enregistrée.',exact=False).wait_for()
   page.goto(url+'/admin');page.locator('[name=password]').fill('QA-admin-passphrase');page.locator('#login button').click()
   panel=page.locator('section.panel').filter(has=page.get_by_role('heading',name='QA New Shop'))
   panel.wait_for();panel.locator('[name=reference]').fill('QA-RECEIPT');page.once('dialog',lambda d:d.accept());panel.get_by_role('button',name='Enregistrer 19 DT et activer 30 jours').click()
   page.get_by_text('Modification enregistrée.',exact=True).wait_for()
   panel.locator('[name=radius]').first.fill('2500');panel.get_by_role('button',name='Enregistrer le rayon').click();page.get_by_text('Modification enregistrée.',exact=True).wait_for()
   assert panel.locator('[name=radius]').first.input_value()=='2500'
   page.once('dialog',lambda d:d.accept());panel.get_by_role('button',name='Bloquer',exact=True).click();page.get_by_text('Modification enregistrée.',exact=True).wait_for()
   panel.get_by_text('blocked',exact=False).wait_for()
   assert not errors,errors
   b.close()
  print('PASS browser: exact pin registration, pending, admin cash activation, radius and blocking')
 finally:server.terminate();server.wait(timeout=10)
