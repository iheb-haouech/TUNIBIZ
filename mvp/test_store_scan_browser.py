import tempfile,os,subprocess,sys,time,requests,shutil,re
from pathlib import Path
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 env={**os.environ,'TUNIBIZ_ENV':'test'}
 server=subprocess.Popen([sys.executable,'-c',"from app import app;app.run(host='127.0.0.1',port=8879,debug=False)"],cwd=p,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 base='http://127.0.0.1:8879'
 try:
  for _ in range(50):
   try:
    if requests.get(base,timeout=.5).ok:break
   except requests.RequestException:time.sleep(.3)
  else:raise AssertionError('Server unavailable')
  pw=re.search(r'Mot de passe: (.+)',(p/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
  with sync_playwright() as w:
   try:b=w.chromium.launch(headless=True)
   except Exception:b=w.chromium.launch(channel='msedge',headless=True)
   merchant=b.new_context(viewport={'width':390,'height':844}).new_page();client=b.new_context(viewport={'width':390,'height':844}).new_page();errors=[]
   for page in (merchant,client):page.on('pageerror',lambda e:errors.append(str(e)))
   client.goto(base+'/join/demo');client.locator('#join').click()
   client.locator('#toggle').click();client.locator('[name=name]').fill('Browser QA');client.locator('[name=email]').fill('browser@example.test');client.locator('[name=password]').fill('Test-consumer-password');client.locator('#account-form button').click()
   client.once('dialog',lambda d:d.accept());client.get_by_role('button',name='Confirmer le scan du commerce').click()
   client.get_by_text('Bienvenue : +3 points !',exact=True).wait_for()
   assert client.locator('.wallet-points').inner_text()=='3 pts'
   client.goto(base+'/join/demo');client.locator('#join').click();client.once('dialog',lambda d:d.accept());client.get_by_role('button',name='Confirmer le scan du commerce').click()
   client.get_by_text('Demande envoyée.',exact=False).wait_for()
   merchant.goto(base+'/crm');merchant.locator('[name=email]').fill('demo@tunibiz.local');merchant.locator('[name=password]').fill(pw);merchant.locator('#login button').click()
   merchant.get_by_role('link',name='QR & validations').click()
   merchant.locator('#queue form').wait_for();assert merchant.locator('#queue input').input_value()=='1'
   merchant.locator('#queue input').fill('5');merchant.get_by_role('button',name='Valider cet achat').click()
   merchant.get_by_text('Validé : +5 points',exact=True).wait_for()
   client.locator('#refresh').click();client.get_by_text('8 pts',exact=True).wait_for()
   assert not errors,errors
   assert client.evaluate('document.documentElement.scrollWidth <= innerWidth') and merchant.evaluate('document.documentElement.scrollWidth <= innerWidth')
   b.close()
  print('PASS browser QR landing, registration, first bonus, default=1, editable=5, merchant approval, wallet refresh and responsive layout')
 finally:server.terminate();server.wait(timeout=10)
