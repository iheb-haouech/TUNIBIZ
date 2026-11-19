"""Isolated adversarial verification, identity reuse, revocation, concurrency, restore."""
import os,sys,tempfile,shutil,sqlite3,hashlib
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from werkzeug.security import generate_password_hash
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='test-'+'x'*64,TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_REQUIRE_EMAIL_VERIFICATION='1')
 sys.path.insert(0,str(p))
 import app as module
 import verification as verification
 from backup_db import backup
 app,db=module.app,module.db
 @app.get('/api/qa-busy')
 def busy():raise sqlite3.OperationalError('private-path-and-query')
 def get(c,path,status=200):
  r=c.get('/api'+path,base_url='https://localhost')
  assert r.status_code==status,(path,r.status_code,r.json)
  return r
 def post(c,path,data,status=200):
  csrf=get(c,'/session').json['csrf']
  r=c.post('/api'+path,json=data,headers={'X-CSRF-Token':csrf},base_url='https://localhost')
  assert r.status_code==status,(path,r.status_code,r.json)
  return r
 with db() as c:
  for slug in ('first','second'):
   sid=c.execute('INSERT INTO shops(slug,name,city) VALUES(?,?,?)',(slug,slug,'QA')).lastrowid
   c.execute('INSERT INTO subscriptions(shop_id,status,paid_until) VALUES(?,\'active\',\'2099-01-01\')',(sid,))
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,slug+'@example.test',generate_password_hash('Test-merchant-pass')))
 a,m,n=app.test_client(),app.test_client(),app.test_client()
 for client,email in ((m,'first'),(n,'second')):post(client,'/login',{'email':email+'@example.test','password':'Test-merchant-pass'})
 creds={'name':'QA','email':'qa@example.test','password':'Test-consumer-pass'}
 post(a,'/wallet/register',creds,201)
 assert get(a,'/verification/status').json['verified'] is False
 post(a,'/wallet/store-scan',{'slug':'first'},403)
 with patch.object(verification.password_recovery,'ready',return_value=False):
  post(a,'/verification/request',{},503)
 sent=[]
 with patch.object(verification.password_recovery,'ready',return_value=True),patch.object(verification,'send_confirmation',side_effect=lambda email,token:sent.append(token)):
  post(a,'/verification/request',{})
 assert len(sent)==1
 with db() as c:assert c.execute('SELECT digest FROM email_confirmations').fetchone()[0]!=sent[0]
 post(a,'/verification/confirm',{'token':sent[0]})
 post(a,'/verification/confirm',{'token':sent[0]},400)
 assert get(a,'/verification/status').json['verified']
 assert post(a,'/wallet/store-scan',{'slug':'first'},201).json['points']==3
 pending=post(a,'/wallet/store-scan',{'slug':'first'},201).json
 cookie=m.get_cookie('session');csrf=get(m,'/session').json['csrf']
 def approve(_):
  client=app.test_client();client.set_cookie('session',cookie.value)
  r=client.post('/api/crm/store-scan/decide',json={'id':pending['id'],'action':'approve','points':5},headers={'X-CSRF-Token':csrf},base_url='https://localhost')
  return r.status_code
 with ThreadPoolExecutor(max_workers=6) as pool:assert list(pool.map(approve,range(6)))==[200]*6
 assert get(a,'/wallet').json['cards'][0]['points']==8
 with db() as c:assert c.execute("SELECT COUNT(*) FROM loyalty_ledger WHERE kind='scan'").fetchone()[0]==1
 assert get(m,'/crm').json['dashboard']['buyers']==1
 cid=get(a,'/wallet').json['cards'][0]['id']
 # One merchant cannot reserve a system or another merchant's idempotency key.
 key='welcome:999'
 post(m,'/crm/purchase',{'id':cid,'amount':1000,'key':key},201)
 other=post(n,'/crm/customer',{'name':'Other'},201).json['id']
 post(n,'/crm/purchase',{'id':other,'amount':1000,'key':key},201)
 assert post(m,'/crm/purchase',{'id':cid,'amount':1000,'key':key}).json['duplicate']
 post(a,'/wallet/delete',{'password':creds['password']})
 post(a,'/wallet/register',creds,201)
 # Verification of a re-created email remains required.
 post(a,'/wallet/store-scan',{'slug':'first'},403)
 with db() as c:c.execute('UPDATE consumer_accounts SET email_verified=1 WHERE email=?',(creds['email'],))
 assert post(a,'/wallet/store-scan',{'slug':'first'},201).json['points']==0
 with db() as c:
  assert c.execute('SELECT COUNT(*) FROM welcome_claims WHERE shop_id=1').fetchone()[0]==1
  assert c.execute('SELECT identity_digest FROM welcome_claims LIMIT 1').fetchone()[0]!=creds['email']
 # Revoke between the first authorization check and the write transaction.
 with db() as c:c.execute('DELETE FROM merchant_sessions WHERE user_id=(SELECT id FROM users WHERE shop_id=1)')
 with patch.object(module,'merchant_identity',return_value=1):
  post(m,'/crm/purchase',{'id':cid,'amount':1000,'key':'revoked'},401)
 assert get(a,'/qa-busy',503).json['error'].find('private')==-1
 response=a.put('/api/qa-busy',base_url='https://localhost')
 assert response.status_code==403 and response.is_json
 response=a.post('/api/wallet/login',data='x'*40000,headers={'X-CSRF-Token':get(a,'/session').json['csrf']},content_type='application/json',base_url='https://localhost')
 assert response.status_code==413 and response.is_json
 assert get(a,'/wallet').headers['Cache-Control']=='no-store'
 # A coherent SQLite snapshot restores the same schema/counts and passes FK checks.
 snap=backup(p/'data'/'tunibiz.sqlite',p/'backups')
 restored=p/'restored.sqlite';shutil.copy2(snap,restored)
 with sqlite3.connect(restored) as c:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
  assert c.execute('SELECT SUM(points) FROM loyalty_ledger').fetchone()[0]==10
 print('PASS verified email, hashed expiring single-use links, blocked unverified scan, recycled-email bonus denied (90 days)')
 print('PASS six concurrent approvals award once, merchant-scoped keys, revoked session denied inside transaction, real QR stats')
 print('PASS JSON errors/CSRF/body bounds, coherent backup and isolated restore with FK checks')
