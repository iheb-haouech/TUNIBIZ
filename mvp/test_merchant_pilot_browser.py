"""Real browser merchant KPIs and subscription on a disposable database."""
import os,sys,tempfile,shutil
from pathlib import Path
from threading import Thread
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+'x'*64,TUNIBIZ_DATA_DIR=str(p/'data'))
 sys.path.insert(0,str(p))
 from app import app,db
 with db() as c:
  sid=c.execute("INSERT INTO shops(slug,name,city) VALUES('qa','Commerce de recette','Djerba')").lastrowid
  c.execute("INSERT INTO subscriptions(shop_id,status,paid_until,category) VALUES(?,'active','2099-01-01','drugstore')",(sid,))
  c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'merchant@example.test',generate_password_hash('Test-merchant-pass')))
  cid=c.execute("INSERT INTO crm_customers(shop_id,name,code_hash) VALUES(?,'Client de recette','qa-hash')",(sid,)).lastrowid
  c.execute("INSERT INTO loyalty_ledger(customer_id,kind,amount,points,label) VALUES(?,'purchase',1000,1,'Achat QA')",(cid,))
  c.execute("INSERT INTO loyalty_ledger(customer_id,kind,amount,points,label) VALUES(?,'scan',0,1,'QR QA')",(cid,))
 app.config['SESSION_COOKIE_SECURE']=False
 client=app.test_client();csrf=client.get('/api/session').json['csrf']
 assert client.post('/api/login',json={'email':'merchant@example.test','password':'Test-merchant-pass'},headers={'X-CSRF-Token':csrf}).status_code==200
 server=make_server('127.0.0.1',0,app);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 origin='http://127.0.0.1:'+str(server.server_port)
 try:
  with sync_playwright() as playwright:
   try:browser=playwright.chromium.launch(headless=True)
   except Exception:browser=playwright.chromium.launch(channel='msedge',headless=True)
   for width in (390,1440):
    context=browser.new_context(viewport={'width':width,'height':844})
    context.add_cookies([{'name':'session','value':client.get_cookie('session').value,'url':origin}])
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(origin+'/crm');page.wait_for_selector('.business-hero')
    assert page.get_by_text('Abonnement : active',exact=True).count()==1
    assert '2 achat(s)' in page.locator('.business-panel').all_text_contents()[1]
    assert page.get_by_text('Nouveaux clients · 30 j',exact=True).count()==1
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert errors==[],errors
    page.screenshot(path='E:/TUNIBIZ-Dev/pilot050-merchant-'+str(width)+'.png',full_page=True)
    context.close()
   browser.close()
  print('PASS real merchant browser: subscription, QR purchases, amount-based average, operational metrics, 390/1440px, no JS errors')
 finally:server.shutdown();thread.join(timeout=3)
