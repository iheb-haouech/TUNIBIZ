"""Isolated multi-merchant integration tests, no live database."""
from pathlib import Path
import tempfile,shutil,subprocess,sys,time,requests,re,sqlite3,uuid
from playwright.sync_api import sync_playwright
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for name in ['app.py','crm.py','leads.py','nearby.py','loyalty_qr.py','wallet.py','merchant_dashboard.py','subscriptions.py','google_identity.py','analytics.py','store_scan.py','password_recovery.py']:shutil.copy2(P/name,p/name)
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
   c.execute("INSERT INTO subscriptions(shop_id,status,paid_until) VALUES(?,'active','2099-12-31')",(sid,))
   c.execute("INSERT INTO users(shop_id,email,password) VALUES(?,?,?)",(sid,'second@example.test',generate_password_hash('Second-test-password')))
  m1,m2=client(),client();post(m1,'/login',{'email':'demo@tunibiz.local','password':pw});post(m2,'/login',{'email':'second@example.test','password':'Second-test-password'})
  cards=[]
  for m,n,points in [(m1,'Wallet first',135),(m2,'Wallet second',80)]:
   card=post(m,'/crm/customer',{'name':n,'phone':'','consent':False},201);cards.append(card)
   post(m,'/crm/purchase',{'id':card['id'],'amount':points*1000,'key':str(uuid.uuid4())},201)
   post(m,'/crm/reward',{'title':'QA Reward','cost':100},201)
  d1=get(m1,'/crm')['dashboard'];d2=get(m2,'/crm')['dashboard']
  assert len(d1['daily'])==30 and sum(x['amount'] for x in d1['daily'])==135000
  assert sum(x['amount'] for x in d2['daily'])==80000 and d1['buyers']==1 and d1['repeat_buyers']==0
  assert get(client(),'/crm',401)
  print('PASS dashboard: timeline, merchant isolation and auth')
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
   page.goto(url+'/crm');page.locator('[name=email]').fill('demo@tunibiz.local');page.locator('[name=password]').fill(pw);page.locator('#login button').click()
   page.locator('.business-hero').wait_for();assert page.locator('.business-bar').count()==7
   assert page.locator('.business-amount').inner_text()=='135.000 DT'
   page.locator('[data-period="30"]').click();assert page.locator('.business-bar').count()==30
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
   page.locator('[data-go=customers]').click();page.locator('#resolveqr').wait_for()
   page.goto(url+'/wallet');page.locator('[name=email]').fill(creds['email']);page.locator('[name=password]').fill(creds['password']);page.locator('#account-form button').click()
   page.locator('.wallet-card').first.wait_for();assert page.locator('.wallet-card').count()==2
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
   page.locator('[data-open="'+str(cards[1]['id'])+'"]').click();page.locator('#makeqr').wait_for();assert 'QA Second' in page.locator('.card').inner_text()
   page.goto(url+'/wallet');page.locator('#logout').click();page.locator('#account-form').wait_for()
   page.goto(url+'/account-deletion');page.get_by_role('link',name='Accéder au portefeuille et supprimer mon compte').click()
   page.locator('[name=email]').fill(creds['email']);page.locator('[name=password]').fill(creds['password']);page.locator('#account-form button').click()
   page.locator('#delete-account').click();page.locator('#delete-form [name=password]').fill('wrong-password');page.locator('#delete-form button[type=submit]').click()
   page.get_by_text('Mot de passe incorrect',exact=True).wait_for()
   page.locator('#delete-form [name=password]').fill(creds['password']);page.locator('#delete-form button[type=submit]').click()
   page.get_by_text('Compte supprimé.',exact=True).wait_for()
   assert not errors,errors;browser.close()
  get(a,'/wallet',401);get(a,'/loyalty',401)
  with sqlite3.connect(p/'data/tunibiz.sqlite') as c:
   assert c.execute('SELECT COUNT(*) FROM consumer_accounts WHERE email=?',(creds['email'],)).fetchone()[0]==0
   for card in cards:
    assert c.execute('SELECT name,phone,consent FROM crm_customers WHERE id=?',(card['id'],)).fetchone()==('Client anonymise','',0)
    assert c.execute('SELECT COUNT(*) FROM wallet_cards WHERE customer_id=?',(card['id'],)).fetchone()[0]==0
   assert c.execute('SELECT COUNT(*) FROM consumer_accounts WHERE email=?',('other@example.test',)).fetchone()[0]==1
  stolen=client();stolen.cookies.update(m1.cookies)
  post(m1,'/logout',{});get(stolen,'/crm',401)
  print('PASS merchant logout revokes copied session cookie')
  print('PASS account deletion, wrong password, all sessions revoked, other account unaffected, cards anonymized')
  print('PASS browser: wallet login, two cards, selected card, logout, responsive mobile and no JS errors')
 finally:server.terminate();server.wait(timeout=10)
