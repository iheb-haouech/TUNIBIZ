"""Real scan accounting, merchant scoping and Facebook destinations, on an isolated DB."""
import os,sys,tempfile,shutil
from pathlib import Path
from werkzeug.security import generate_password_hash

P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+('x'*64),TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_REQUIRE_EMAIL_VERIFICATION='1')
 sys.path.insert(0,str(p))
 from app import app,db
 with db() as c:
  for slug,state in [('first','active'),('second','active'),('blocked','blocked')]:
   sid=c.execute('INSERT INTO shops(slug,name,city) VALUES(?,?,?)',(slug,slug,'Test')).lastrowid
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,slug+'@example.test',generate_password_hash('Test-merchant-password')))
   c.execute('INSERT INTO subscriptions(shop_id,status,paid_until) VALUES(?,?,?)',(sid,state,'2099-01-01'))
 def client():
  a=app.test_client();return a,{'X-CSRF-Token':a.get('/api/session',base_url='https://localhost').json['csrf']}
 def post(a,path,data,status=200):
  r=a[0].post('/api'+path,json=data,headers=a[1],base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.json);return r.json
 def get(a,path,status=200):
  r=a[0].get('/api'+path,base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.json);return r.json
 a,m,n,guest=client(),client(),client(),client()
 post(m,'/login',{'email':'first@example.test','password':'Test-merchant-password'})
 post(n,'/login',{'email':'second@example.test','password':'Test-merchant-password'})
 settings='/crm/store-qr/settings';target='https://www.facebook.com/qa-first'
 post(guest,settings,{'facebook_url':target},401)
 assert m[0].post('/api'+settings,json={'facebook_url':target},base_url='https://localhost').status_code==403
 for bad in ['http://facebook.com/page','https://facebook.com.evil.test/page','https://evil.test/facebook.com/page','https://facebook.com@evil.test/page','https://facebook.com:444/page','javascript:alert(1)','//facebook.com/page','https://facebook.com','https://facebook.com/pa ge','https://www.facebook.com/\\evil.test','https://user@facebook.com/page',None]:
  post(m,settings,{'facebook_url':bad},400)
 post(m,settings,{'facebook_url':target,'shop_id':2})
 assert get(guest,'/store/first')['shop']['facebook_url']==target
 assert get(guest,'/store/second')['shop']['facebook_url']==''
 assert get(m,'/crm/store-qr')['url']=='https://ihebhaouech.pythonanywhere.com/join/first'
 assert get(m,'/crm/store-qr')['facebook_url']==target
 get(guest,'/store/blocked',404)
 for _ in range(3):assert a[0].get('/join/first',base_url='https://localhost').status_code==200
 with db() as c:assert c.execute('SELECT COUNT(*) FROM loyalty_ledger').fetchone()[0]==0
 post(guest,'/wallet/store-scan',{'slug':'first'},401)
 post(a,'/wallet/register',{'name':'QA Consumer','email':'qa@example.test','password':'Test-consumer-password'},201)
 post(a,'/wallet/store-scan',{'slug':'first'},403)
 with db() as c:c.execute("UPDATE consumer_accounts SET email_verified=1 WHERE email='qa@example.test'")
 welcome=post(a,'/wallet/store-scan',{'slug':'first','facebook_url':'https://evil.test'},201)
 assert welcome['status']=='welcome' and welcome['points']==3 and welcome['facebook_url']==target
 pending=post(a,'/wallet/store-scan',{'slug':'first'},201)
 repeat=post(a,'/wallet/store-scan',{'slug':'first'})
 assert repeat['duplicate'] and pending['id']==repeat['id'] and repeat['facebook_url']==target
 assert get(a,'/wallet')['cards'][0]['points']==3
 post(n,'/crm/store-scan/decide',{'id':pending['id'],'action':'approve'},404)
 post(m,'/crm/store-scan/decide',{'id':pending['id'],'action':'approve','points':5})
 post(m,'/crm/store-scan/decide',{'id':pending['id'],'action':'approve','points':5})
 assert get(a,'/wallet')['cards'][0]['points']==8
 post(m,settings,{'facebook_url':''})
 assert get(a,'/store/first')['shop']['facebook_url']==''
 assert get(m,'/crm/store-qr')['url'].endswith('/join/first')
 post(n,settings,{'facebook_url':'https://m.facebook.com/qa-second'})
 second=post(a,'/wallet/store-scan',{'slug':'second'},201)
 assert second['facebook_url']=='https://m.facebook.com/qa-second'
 with db() as c:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert not c.execute('PRAGMA foreign_key_check').fetchall()
 print('PASS: stable QR, merchant-only Facebook settings, CSRF, host validation, tenant isolation, no points on GET/anonymous/unverified, truthful welcome/pending, retry idempotency and merchant approval')
