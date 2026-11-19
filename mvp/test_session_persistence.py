"""Check persistent sessions, revocation and expiry on isolated production-mode DB."""
import os,sys,tempfile,shutil,time
from pathlib import Path
from werkzeug.security import generate_password_hash
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+('x'*64),TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash('Test-admin-password'))
 sys.path.insert(0,str(p))
 from app import app,db
 base='https://localhost'
 with db() as c:
  sid=c.execute("INSERT INTO shops(slug,name,city) VALUES('qa','QA','Test')").lastrowid
  c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'qa-merchant@example.test',generate_password_hash('Test-merchant-password')))
  c.execute("INSERT INTO subscriptions(shop_id,status,paid_until) VALUES(?,'active','2099-01-01')",(sid,))
 def get(a,path):return a.get('/api'+path,base_url=base)
 def post(a,path,body,status=200):
  token=get(a,'/session').json['csrf']
  r=a.post('/api'+path,json=body,headers={'X-CSRF-Token':token},base_url=base)
  assert r.status_code==status,(path,r.status_code,r.json)
  return r
 def check_cookie(a,r):
  h=r.headers.get('Set-Cookie','')
  assert all(x in h for x in ('Expires=','Secure','HttpOnly','SameSite=Lax')),h
  cookie=a.get_cookie('session')
  assert cookie is not None and cookie.expires is not None
  return cookie.value
 def reopen(value):
  a=app.test_client()
  a.set_cookie('session',value,domain='localhost')
  return a
 a=app.test_client();m=app.test_client()
 w=check_cookie(a,post(a,'/wallet/register',{'name':'QA Customer','email':'qa@example.test','password':'Test-wallet-password'},201))
 mk=check_cookie(m,post(m,'/login',{'email':'qa-merchant@example.test','password':'Test-merchant-password'}))
 a2=reopen(w);m2=reopen(mk)
 assert get(a2,'/wallet').json['profile']['name']=='QA Customer'
 assert get(m2,'/crm').status_code==200
 assert get(m2,'/wallet').status_code==401
 assert get(a2,'/crm').status_code==401
 with db() as c:
  for table in ('wallet_sessions','merchant_sessions'):
   expires=c.execute('SELECT expires FROM '+table).fetchone()[0]
   assert 29*86400<expires-time.time()<=30*86400
 with db() as c:c.execute('UPDATE wallet_sessions SET expires=?',(int(time.time())+86400,))
 renewed=get(a2,'/wallet');assert renewed.status_code==200 and 'Expires=' in renewed.headers.get('Set-Cookie','')
 with db() as c:assert c.execute('SELECT expires FROM wallet_sessions').fetchone()[0]-time.time()>29*86400
 post(a2,'/wallet/logout',{})
 assert get(reopen(w),'/wallet').status_code==401
 # Merchant block invalidates even a saved cookie.
 with db() as c:c.execute("UPDATE subscriptions SET status='blocked' WHERE shop_id=?",(sid,))
 assert get(reopen(mk),'/crm').status_code==401
 with db() as c:c.execute("UPDATE subscriptions SET status='active' WHERE shop_id=?",(sid,))
 post(m2,'/logout',{})
 assert get(reopen(mk),'/crm').status_code==401
 w2=check_cookie(a,post(a,'/wallet/login',{'email':'qa@example.test','password':'Test-wallet-password'}))
 with db() as c:c.execute('UPDATE wallet_sessions SET expires=0')
 assert get(reopen(w2),'/wallet').status_code==401
 print('PASS persistent secure cookies, separate reopened sessions, 30-day expiry, role isolation, logout revocation and merchant blocking')
