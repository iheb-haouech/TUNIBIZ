"""End-to-end UI on a disposable DB. Screenshots contain labelled QA fixtures."""
import os,sys,shutil,tempfile,io,base64,json,secrets
from pathlib import Path
from threading import Thread
from datetime import date,timedelta
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
out=Path(sys.argv[1]) if len(sys.argv)>1 else P.parent/'docs/v052/screenshots'
out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+'x'*64,TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash('QA-admin-password'),TUNIBIZ_REQUIRE_EMAIL_VERIFICATION='0')
 sys.path.insert(0,str(p))
 from app import app,db
 from qa_support import publish_fixture
 with db() as c:
  for sid,name in ((1,'Commerce de recette — TEST'),(2,'Café de recette — TEST')):
   c.execute('INSERT INTO shops(id,slug,name,city) VALUES(?,?,?,?)',(sid,'qa'+str(sid),name,'Djerba'))
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'m'+str(sid)+'@example.test',generate_password_hash('QA-merchant-password')))
   c.execute("INSERT INTO subscriptions(shop_id,status,paid_until,category) VALUES(?,'active','2099-01-01',?)",(sid,'drugstore' if sid==1 else 'coffee'))
  for i in range(4):
   cid=c.execute('INSERT INTO crm_customers(shop_id,name,phone,phone_normalized,code_hash) VALUES(1,?,?,?,?)',('Client de recette '+str(i),'+2162012345'+str(i),'+2162012345'+str(i),secrets.token_hex(32))).lastrowid
   c.execute("INSERT INTO loyalty_ledger(customer_id,kind,points,label) VALUES(?,'manual',?,'Points de recette')",(cid,20+i*10))
  c.execute("INSERT INTO rewards(shop_id,title,cost,description) VALUES(1,'Avantage de recette',100,'Conditions de test')")
 for sid in (1,2):publish_fixture(db,sid)
 m,a,ad=[app.test_client() for _ in range(3)]
 def post(cli,path,body):
  r=cli.post('/api'+path,json=body,base_url='https://localhost',headers={'X-CSRF-Token':cli.get('/api/session',base_url='https://localhost').json['csrf']});assert r.status_code<300,(path,r.json);return r.json
 post(m,'/login',{'email':'m1@example.test','password':'QA-merchant-password'})
 post(a,'/wallet/register',{'name':'Client de recette TEST','email':'qa@example.test','password':'QA-consumer-password'})
 post(ad,'/admin/login',{'password':'QA-admin-password'})
 promo=post(m,'/commerce/promotion',{'title':'−20 % — Offre de recette','description':'Exemple réservé à la recette, pas une offre commerciale réelle.','starts':str(date.today()),'ends':str(date.today()+timedelta(days=10)),'benefit':'discount','discount':20})
 post(ad,'/commerce/sponsor',{'shop_id':1,'title':'À découvrir — Test','description':'Bannière de recette identifiée.','starts':str(date.today()),'ends':str(date.today()+timedelta(days=10)),'status':'active','priority':1})
 app.config['SESSION_COOKIE_SECURE']=False
 server=make_server('127.0.0.1',0,app);thread=Thread(target=server.serve_forever,daemon=True);thread.start();origin='http://127.0.0.1:'+str(server.server_port)
 results=[]
 try:
  with sync_playwright() as pw:
   if os.name=='nt':
    try:browser=pw.chromium.launch(headless=True)
    except Exception:browser=pw.chromium.launch(channel='msedge',headless=True)
   else:browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-zygote','--single-process','--disable-crash-reporter','--disable-breakpad'])
   for width in (390,1440):
    for mode,path,cli in [('business','/crm',m),('client','/client',a),('admin','/admin',ad)]:
     ctx=browser.new_context(viewport={'width':width,'height':900},device_scale_factor=1)
     ctx.add_cookies([{'name':'session','value':cli.get_cookie('session').value,'url':origin}])
     page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     page.goto(origin+path);page.wait_for_selector('.shell')
     if page.locator('#tn-consent-choice').count():page.locator('#tn-consent-choice [data-consent=no]').click()
     assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(mode,width,'overflow')
     page.screenshot(path=str(out/(mode+'-'+str(width)+'.png')),full_page=True)
     if mode=='business':
      page.locator('[data-nav=clients]:visible').click();page.wait_for_selector('#search-client')
      page.get_by_placeholder('+216 20 123 456').fill('20123450');page.locator('#search-client button').click();page.wait_for_selector('#client-results [data-action="points:1"]')
      page.locator('#client-results [data-action="points:1"]').click();page.locator('dialog [name=points]').fill('15');page.locator('dialog [name=reason]').fill('Attribution QA navigateur');page.locator('dialog [type=submit]').click();page.wait_for_selector('dialog[open]',state='hidden');page.wait_for_selector('#search-client')
      page.locator('[data-nav=promotions]:visible').click();page.wait_for_selector('[data-action=promotion]')
      page.locator('[data-action=promotion]').click();page.locator('dialog [name=title]').fill('Promotion créée au navigateur');page.locator('dialog [name=description]').fill('Conditions test');page.locator('dialog [name=discount]').fill('10');assert page.locator('#live-title').inner_text()=='Promotion créée au navigateur';page.locator('dialog [type=submit]').click();page.wait_for_selector('dialog[open]',state='hidden')
      if width<760:page.locator('[data-nav=more]').click();page.locator('dialog [data-nav=nearby]').click()
      else:page.locator('[data-nav=nearby]').click()
      page.wait_for_selector('#nearby-map');assert page.locator('[data-nav=clients]:visible').count()==1
      page.screenshot(path=str(out/('nearby-'+str(width)+'.png')),full_page=True)
     elif mode=='client':
      assert page.locator('.sponsorcard').count()==1
      page.locator('.nav [data-nav=explore]').click();page.wait_for_selector('#search-stores');page.locator('#search-stores').fill('Djerba');assert page.locator('#store-grid .store').count()==2
      page.locator('#store-grid [data-store="1"]').click();page.wait_for_selector('[data-action=usecode]');page.screenshot(path=str(out/('store-'+str(width)+'.png')),full_page=True)
      page.locator('[data-nav=cards]').click();page.wait_for_selector('.empty');assert 'Votre prochaine carte' in page.locator('.empty').inner_text()
      page.locator('[data-nav=profile]').click();page.wait_for_selector('[data-action=phone]');assert page.locator('[data-action=delete]').count()==1
     else:
      page.locator('.nav [data-nav=sponsors]').click();page.wait_for_selector('[data-action=sponsor]');page.locator('[data-action=sponsor]').click();page.wait_for_selector('dialog [name=title]');page.screenshot(path=str(out/('sponsor-editor-'+str(width)+'.png')),full_page=True);page.locator('dialog .close').click()
     assert errors==[],errors
     results.append({'space':mode,'width':width,'js_errors':errors,'horizontal_overflow':False,'passed':True})
     ctx.close()
   # Signed-out client always lands on login.
   ctx=browser.new_context(viewport={'width':390,'height':844});page=ctx.new_page();page.goto(origin+'/client');page.wait_for_selector('#login');assert page.locator('.nav').count()==0;page.screenshot(path=str(out/'login-390.png'),full_page=True);ctx.close();browser.close()
  (out.parent/'browser-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
  print(json.dumps({'passed':len(results),'screenshots':str(out),'results':results}))
 finally:server.shutdown();thread.join(timeout=3)
