"""Isolated multi-merchant integration tests, no live database."""
from pathlib import Path
import tempfile,shutil,subprocess,sys,time,requests,re,sqlite3,uuid
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for name in ['app.py','crm.py','leads.py','nearby.py','loyalty_qr.py','wallet.py']:shutil.copy2(P/name,p/name)
 shutil.copytree(P/'static',p/'static')
 server=subprocess.Popen([sys.executable,'-c',"from app import app;app.run(host='127.0.0.1',port=8879,debug=False)"],cwd=p,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 url='http://127.0.0.1:8879'
 def client():
  s=requests.Session();s.headers['X-CSRF-Token']=s.get(url+'/api/session').json()['csrf'];return s
 def post(s,path,body,status=200):
  r=s.post(url+'/api'+path,json=body);assert r.status_code==status,(path,r.status_code,r.text);return r.json()
 def get(s,path,status=200):
  r=s.get(url+'/api'+path);assert r.status_code==status,(path,r.status_code,r.text);return r.json()
 try:
  for _ in range(50):
   try:
    if requests.get(url,timeout=.5).ok:break
   except requests.RequestException:time.sleep(.3)
  else:raise AssertionError('Test server unavailable')
  from werkzeug.security import generate_password_hash
  pw=re.search(r'Mot de passe: (.+)',(p/'data/demo-login.txt').read_text(encoding='utf-8')).group(1).strip()
  with sqlite3.connect(p/'data/tunibiz.sqlite') as c:
   sid=c.execute("INSERT INTO shops(slug,name,city) VALUES('qa-second','QA Second','Tunisie')").lastrowid
   c.execute("INSERT INTO users(shop_id,email,password) VALUES(?,?,?)",(sid,'second@example.test',generate_password_hash('Second-test-password')))
  m1,m2=client(),client();post(m1,'/login',{'email':'demo@tunibiz.local','password':pw});post(m2,'/login',{'email':'second@example.test','password':'Second-test-password'})
  cards=[]
  for m,n,points in [(m1,'Wallet first',135),(m2,'Wallet second',80)]:
   card=post(m,'/crm/customer',{'name':n,'phone':'','consent':False},201);cards.append(card)
   post(m,'/crm/purchase',{'id':card['id'],'amount':points*1000,'key':str(uuid.uuid4())},201)
   post(m,'/crm/reward',{'title':'QA Reward','cost':100},201)
  a,b=client(),client();creds={'name':'QA Wallet','email':'wallet@example.test','password':'Long-Test-Passphrase'}
  get(a,'/wallet',401);post(a,'/wallet/register',creds,201);post(b,'/wallet/register',{**creds,'email':'other@example.test'},201)
  for card in cards:post(a,'/wallet/link',{'code':card['code']})
  wallet=get(a,'/wallet');byid={c['id']:c for c in wallet['cards']}
  assert byid[cards[0]['id']]['points']==135 and byid[cards[0]['id']]['eligible']==1
  assert byid[cards[1]['id']]['points']==80 and byid[cards[1]['id']]['eligible']==0
  assert len(wallet['cards'])==2 and 'password' not in wallet['profile']
  post(b,'/wallet/select',{'id':cards[0]['id']},404);post(b,'/wallet/link',{'code':cards[0]['code']},409);post(b,'/wallet/unlink',{'id':cards[0]['id']},404)
  post(a,'/wallet/select',{'id':cards[0]['id']});assert get(a,'/loyalty')['customer']['points']==135
  qr=post(a,'/loyalty/qr',{},201)['token'];post(m2,'/crm/qr/resolve',{'token':qr},404);post(m1,'/crm/qr/resolve',{'token':qr})
  post(a,'/wallet/select',{'id':cards[1]['id']});assert get(a,'/loyalty')['customer']['points']==80
  post(a,'/wallet/logout',{});get(a,'/wallet',401);get(a,'/loyalty',401);post(a,'/wallet/login',creds);assert len(get(a,'/wallet')['cards'])==2
  post(a,'/wallet/select',{'id':cards[0]['id']});post(a,'/wallet/unlink',{'id':cards[0]['id']});get(a,'/loyalty',401);post(a,'/wallet/link',{'code':cards[0]['code']})
  post(a,'/wallet/select',{'id':cards[0]['id']});new=post(m1,'/crm/customer/reset',{'id':cards[0]['id']})['code'];get(a,'/loyalty',401);assert len(get(a,'/wallet')['cards'])==1
  post(a,'/wallet/link',{'code':new});assert len(get(a,'/wallet')['cards'])==2
  with sqlite3.connect(p/'data/tunibiz.sqlite') as c:
   assert c.execute('SELECT password FROM consumer_accounts WHERE email=?',(creds['email'],)).fetchone()[0]!=creds['password']
  print('PASS API: multi-shop balances, eligibility, session, account isolation, QR scope, unlink, code revocation and password hash',flush=True)
  with sync_playwright() as w:
   try:browser=w.chromium.launch(headless=True)
   except Exception:browser=w.chromium.launch(channel='msedge',headless=True)
   page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(url+'/wallet');page.locator('[name=email]').fill(creds['email']);page.locator('[name=password]').fill(creds['password']);page.locator('#account-form button').click()
   page.locator('.wallet-card').first.wait_for();assert page.locator('.wallet-card').count()==2
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
   page.locator('[data-open="'+str(cards[1]['id'])+'"]').click();page.locator('#makeqr').wait_for();assert 'QA Second' in page.locator('.card').inner_text()
   page.goto(url+'/wallet');page.locator('#logout').click();page.locator('#account-form').wait_for()
   assert not errors,errors;browser.close()
  print('PASS browser: wallet login, two cards, selected card, logout, responsive mobile and no JS errors')
 finally:server.terminate();server.wait(timeout=10)
