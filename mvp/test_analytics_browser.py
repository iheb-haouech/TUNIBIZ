"""Consent, one loader, sanitized analytics payloads; --live uses Google's real SDK in debug mode."""
import os,sys,tempfile,shutil,json,hashlib,base64,time
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit,parse_qs
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
 from app import app
 app.config['SESSION_COOKIE_SECURE']=False
 client=app.test_client();csrf=client.get('/api/session').json['csrf']
 email='qa.analytics@example.test'
 assert client.post('/api/wallet/register',json={'name':'Analytics QA','email':email,'password':'QA-analytics-test-pass'},headers={'X-CSRF-Token':csrf}).status_code==201
 server=make_server('127.0.0.1',0,app);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
 origin='http://127.0.0.1:'+str(server.server_port)
 try:
  with sync_playwright() as playwright:
   try:browser=playwright.chromium.launch(headless=True)
   except Exception:browser=playwright.chromium.launch(channel='msedge',headless=True)
   context=browser.new_context(viewport={'width':390,'height':844})
   context.add_cookies([{'name':'session','value':client.get_cookie('session').value,'url':origin}])
   requested=[]
   def stub(route):
    requested.append(route.request.url);route.fulfill(content_type='application/javascript',body='window.__tnGoogleReady=true;')
   context.route('https://www.googletagmanager.com/**',stub)
   page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(origin+'/wallet?email='+email+'#sensitive-qa-token');page.wait_for_selector('#tn-consent-choice')
   page.wait_for_timeout(200)
   assert requested==[],requested
   assert page.get_by_text('Bonjour Analytics QA',exact=True).count()==1
   page.locator('#tn-consent-choice [data-consent=yes]').click()
   page.wait_for_function('window.__tnGoogleReady===true')
   assert len(requested)==1 and '/gtm.js?id=GTM-N7B5938K' in requested[0],requested
   assert page.locator('script[src*="/gtag/js"]').count()==0
   page.evaluate("window.tunibizAnalytics('stores_open')")
   page.wait_for_timeout(300)
   layer=page.evaluate("window.dataLayer.map(x=>Array.isArray(x)?x:(x&&typeof x==='object'&&'0' in x?Array.from(x):x))")
   wire=json.dumps(layer,default=str)
   assert email not in wire and 'sensitive-qa-token' not in wire,wire
   commands=[x for x in layer if isinstance(x,list)]
   defaults=[x for x in commands if x[:2]==['consent','default']]
   grants=[x for x in commands if x[:2]==['consent','update']]
   assert defaults[0][2]['analytics_storage']=='denied'
   assert grants[-1][2]['analytics_storage']=='granted'
   assert grants[-1][2]['ad_user_data']=='denied' and grants[-1][2]['ad_storage']=='denied'
   assert len([x for x in commands if x[:2]==['event','page_view']])==1
   assert any(x[:2]==['event','tn_stores_open'] for x in commands)
   page.get_by_role('button',name='Préférences de statistiques',exact=True).click()
   page.get_by_role('button',name='Refuser / désactiver',exact=True).click()
   page.wait_for_load_state('domcontentloaded');page.wait_for_selector('#wallet-app')
   assert page.evaluate("localStorage.getItem('tn_analytics')")=='no'
   assert len(requested)==1,requested
   assert any(c['name']=='session' for c in context.cookies())
   assert errors==[],errors
   # A saved opt-in never loads Google on administration or token recovery pages.
   guarded=browser.new_context();guarded.add_init_script("localStorage.setItem('tn_analytics','yes')")
   forbidden=[];guarded.route('https://www.googletagmanager.com/**',lambda route:(forbidden.append(route.request.url),route.abort()))
   gp=guarded.new_page()
   for path in ('/admin','/reset-password#sensitive-qa-token','/verify-email#sensitive-qa-token'):
    gp.goto(origin+path);gp.wait_for_timeout(100)
   assert forbidden==[],forbidden
   guarded.close();context.close()
   print('PASS consent: zero Google before choice, one GTM loader, no duplicate page_view, sanitized URL, ads denied, withdrawal retains account, sensitive routes excluded')
   if '--live' in sys.argv:
    live=browser.new_context(viewport={'width':390,'height':844})
    live.add_cookies([{'name':'session','value':client.get_cookie('session').value,'url':origin}])
    live.add_init_script("localStorage.setItem('tn_analytics','yes');window.dataLayer=[];window.dataLayer.push((function(){return arguments;})('set','debug_mode',true));")
    page=live.new_page();hits=[];responses=[]
    def record(request):
     if 'google-analytics.com' in request.url and 'collect' in request.url:
      hits.append({'url':request.url,'body':request.post_data or ''})
    page.on('request',record)
    page.on('response',lambda response:responses.append(response.status) if 'google-analytics.com' in response.url and 'collect' in response.url else None)
    page.goto(origin+'/wallet?email='+email+'#sensitive-qa-token')
    page.wait_for_timeout(12000)
    payload=json.dumps(hits)
    digest=hashlib.sha256(email.encode()).digest()
    for forbidden in (email,email.replace('@','%40'),'sensitive-qa-token',digest.hex(),base64.urlsafe_b64encode(digest).decode().rstrip('=')):
     assert forbidden not in payload,'Sensitive test data observed in Google request'
    assert hits,'No real Google Analytics collection request observed'
    assert any(200<=status<300 for status in responses),responses
    events=[]
    for hit in hits:
     events+=parse_qs(urlsplit(hit['url']).query).get('en',[])
     for line in hit['body'].splitlines():events+=parse_qs(line).get('en',[])
    assert events.count('page_view')==1,events
    assert 'tn_wallet_open' in events,events
    result={'events':events,'measurement_id':'G-HP8K9C7WD5','container_id':'GTM-N7B5938K','requests':len(hits),'statuses':responses,'sensitive_test_values_absent':True,'scope':'real SDK on isolated local site, debug mode; not GA4 console/production validation'}
    Path('E:/TUNIBIZ-Dev/pilot050-google-live-test.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS real Google transport:',json.dumps(result))
    live.close()
   browser.close()
 finally:server.shutdown();thread.join(timeout=3)
