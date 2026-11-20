"""Browser check: authentication continuation, truthful popup, redirect and cancellation."""
import os,sys,shutil,tempfile
from pathlib import Path
from threading import Thread
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect

P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+'x'*64,TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_REQUIRE_EMAIL_VERIFICATION='0')
 sys.path.insert(0,str(p))
 from app import app,db
 with db() as c:
  for slug in ('first','second'):
   sid=c.execute('INSERT INTO shops(slug,name,city) VALUES(?,?,?)',(slug,'Commerce TEST '+slug,'Djerba')).lastrowid
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,slug+'@example.test',generate_password_hash('QA-merchant-password')))
   c.execute("INSERT INTO subscriptions(shop_id,status,paid_until) VALUES(?,'active','2099-01-01')",(sid,))
 consumer=app.test_client();merchant=app.test_client()
 def post(cli,path,data):
  headers={'X-CSRF-Token':cli.get('/api/session',base_url='https://localhost').json['csrf']}
  r=cli.post('/api'+path,headers=headers,json=data,base_url='https://localhost');assert r.status_code<300,r.json;return r.json
 post(consumer,'/wallet/register',{'name':'Client TEST','email':'qa@example.test','password':'QA-consumer-password'})
 post(merchant,'/login',{'email':'first@example.test','password':'QA-merchant-password'})
 app.config['SESSION_COOKIE_SECURE']=False
 server=make_server('127.0.0.1',0,app);thread=Thread(target=server.serve_forever,daemon=True);thread.start();origin='http://127.0.0.1:'+str(server.server_port)
 try:
  with sync_playwright() as pw:
   if os.name=='nt':browser=pw.chromium.launch(channel='msedge',headless=True)
   else:browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-zygote','--disable-dev-shm-usage'])
   def context(cli=None):
    ctx=browser.new_context(viewport={'width':390,'height':844})
    if cli:ctx.add_cookies([{'name':'session','value':cli.get_cookie('session').value,'url':origin}])
    ctx.add_init_script("localStorage.setItem('tn_analytics','no')")
    return ctx
   # Merchant configures one stored destination, without changing the printed QR.
   ctx=context(merchant);page=ctx.new_page();page.goto(origin+'/merchant-qr');page.locator('[name=facebook_url]').fill('https://www.facebook.com/qa-first');page.get_by_role('button',name='Enregistrer le lien Facebook').click();expect(page.get_by_text('Lien enregistré. Le QR imprimé reste le même.')).to_be_visible();ctx.close()
   # Signed-out scan resumes after a normal consumer login.
   ctx=context();page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('https://www.facebook.com/qa-first',lambda route:route.fulfill(status=200,content_type='text/html',body='<h1>Facebook TEST destination</h1>'))
   page.goto(origin+'/join/first');expect(page.locator('#join')).to_be_visible();expect(page.locator('#confirm-scan')).to_be_hidden()
   page.locator('#join').click();page.locator('#login [name=email]').fill('qa@example.test');page.locator('#login [name=password]').fill('QA-consumer-password');page.locator('#login [type=submit]').click()
   page.get_by_role('link',name='Poursuivre mon scan').click();page.locator('#confirm-scan').click();expect(page.locator('#scan-confirmation')).to_be_visible();expect(page.locator('#scan-result')).to_contain_text('+3 points de bienvenue crédités')
   assert '/join/first' in page.url
   page.wait_for_url('https://www.facebook.com/qa-first');assert errors==[],errors
   with db() as c:assert c.execute('SELECT SUM(points) FROM loyalty_ledger').fetchone()[0]==3
   # The same account sees pending, not credited, points; Escape cancels navigation.
   page.goto(origin+'/join/first');page.locator('#confirm-scan').click();expect(page.locator('#scan-result')).to_contain_text('en attente de validation')
   page.keyboard.press('Escape');page.wait_for_timeout(3300);assert page.url==origin+'/join/first'
   with db() as c:assert c.execute('SELECT SUM(points) FROM loyalty_ledger').fetchone()[0]==3
   # No Facebook configured: points still work and there is no external opening.
   page.goto(origin+'/join/second');page.locator('#confirm-scan').click();expect(page.locator('#scan-confirmation')).to_be_visible();expect(page.locator('#facebook-link')).to_be_hidden()
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.get_by_role('button',name='Rester dans TUNIBIZ').click()
   # A failed POST must neither claim success nor redirect.
   page.route('**/api/wallet/store-scan',lambda route:route.fulfill(status=403,content_type='application/json',body='{"error":"Vérifiez votre email avant de rejoindre un commerce."}'))
   page.goto(origin+'/join/first');page.locator('#confirm-scan').click();expect(page.locator('#status')).to_contain_text('Vérifiez votre email');expect(page.locator('#scan-confirmation')).not_to_be_visible();page.wait_for_timeout(3300);assert page.url==origin+'/join/first';assert errors==[],errors
   ctx.close();browser.close()
  print('PASS browser: merchant settings, login continuation, popup before Facebook, correct welcome/pending text, Escape cancels redirect, no Facebook configured, failed scans never redirect, mobile layout and no JS errors')
 finally:server.shutdown();thread.join(timeout=3)
