"""Isolated regression: QR joins, approval, rejection, expiry, idempotency, shop separation."""
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
 with db() as c:
  for slug in ('first','second','blocked'):
   sid=c.execute('INSERT INTO shops(slug,name,city) VALUES(?,?,?)',(slug,slug,'Test')).lastrowid
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,slug+'@example.test',generate_password_hash('Test-merchant-password')))
   c.execute('INSERT INTO subscriptions(shop_id,status,paid_until) VALUES(?,?,?)',(sid,'blocked' if slug=='blocked' else 'active','2099-01-01'))
 def client():
  a=app.test_client();return a,{'X-CSRF-Token':a.get('/api/session',base_url='https://localhost').json['csrf']}
 def post(a,path,data,status=200):
  r=a[0].post('/api'+path,json=data,headers=a[1],base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True));return r.json
 def get(a,path,status=200):
  r=a[0].get('/api'+path,base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True));return r.json
 a,m,n,other=client(),client(),client(),client()
 post(m,'/login',{'email':'first@example.test','password':'Test-merchant-password'})
 post(n,'/login',{'email':'second@example.test','password':'Test-merchant-password'})
 post(a,'/wallet/register',{'name':'QA Customer','email':'qa@example.test','password':'Test-consumer-password'},201)
 post(other,'/wallet/register',{'name':'Other','email':'other@example.test','password':'Test-consumer-password'},201)
 assert a[0].get('/qr/download.png').mimetype=='image/png'
 assert a[0].get('/join/first').status_code==200
 assert get(m,'/crm/store-qr')['url'].endswith('/join/first')
 assert get(n,'/crm/store-qr')['url'].endswith('/join/second')
 get(other,'/crm/store-qr',401)
 post(a,'/wallet/store-scan',{'slug':'blocked'},404)
 assert post(a,'/wallet/store-scan',{'slug':'first'},201)['points']==3
 assert get(m,'/crm')['customers'][0]['name']=='QA Customer'
 assert get(m,'/crm')['customers'][0]['consent']==0
 assert get(a,'/wallet')['cards'][0]['points']==3
 r=post(a,'/wallet/store-scan',{'slug':'first'},201);rid=r['id']
 assert post(a,'/wallet/store-scan',{'slug':'first'})['id']==rid
 assert len(get(m,'/crm/store-scans')['requests'])==1
 assert get(n,'/crm/store-scans')['requests']==[]
 assert get(a,'/wallet')['cards'][0]['points']==3
 post(n,'/crm/store-scan/decide',{'id':rid,'action':'approve','points':6},404)
 post(other,'/crm/store-scan/decide',{'id':rid,'action':'approve','points':6},401)
 post(m,'/crm/store-scan/decide',{'id':rid,'action':'approve','points':1001},400)
 assert post(m,'/crm/store-scan/decide',{'id':rid,'action':'approve','points':5})['points']==5
 assert post(m,'/crm/store-scan/decide',{'id':rid,'action':'approve','points':5})['duplicate']
 post(m,'/crm/store-scan/decide',{'id':rid,'action':'approve','points':6},409)
 assert get(a,'/wallet')['cards'][0]['points']==8
 assert post(a,'/wallet/store-scan',{'slug':'second'},201)['points']==3
 assert {x['shop']:x['points'] for x in get(a,'/wallet')['cards']}=={'first':8,'second':3}
 with db() as c:c.execute("UPDATE store_scan_requests SET decided=0 WHERE id=?",(rid,))
 r=post(a,'/wallet/store-scan',{'slug':'first'},201);post(m,'/crm/store-scan/decide',{'id':r['id'],'action':'reject'})
 with db() as c:c.execute("UPDATE store_scan_requests SET decided=0 WHERE id=?",(r['id'],))
 r=post(a,'/wallet/store-scan',{'slug':'first'},201)
 with db() as c:c.execute("UPDATE store_scan_requests SET expires=0 WHERE id=?",(r['id'],))
 post(m,'/crm/store-scan/decide',{'id':r['id'],'action':'approve'},409)
 r=post(a,'/wallet/store-scan',{'slug':'first'},201);assert post(m,'/crm/store-scan/decide',{'id':r['id'],'action':'approve'})['points']==1
 assert {x['shop']:x['points'] for x in get(a,'/wallet')['cards']}=={'first':9,'second':3}
 cid=next(x['id'] for x in get(a,'/wallet')['cards'] if x['shop']=='first')
 post(a,'/wallet/unlink',{'id':cid})
 with db() as c:c.execute("UPDATE store_scan_requests SET decided=0")
 post(a,'/wallet/store-scan',{'slug':'first'},201)
 assert next(x['points'] for x in get(a,'/wallet')['cards'] if x['shop']=='first')==9
 post(a,'/wallet/unlink',{'id':cid})
 post(a,'/wallet/delete',{'password':'Test-consumer-password'})
 with db() as c:
  assert c.execute('SELECT COUNT(*) FROM store_memberships').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM store_scan_requests').fetchone()[0]==0
  assert c.execute("SELECT name FROM crm_customers WHERE id=?",(cid,)).fetchone()[0]=='Client anonymise'
 print('PASS: 2 QR types, 3 welcome, merchant-adjusted +5/default +1, no duplicate, cross-store protection, decline, expiry, rejoin, account removal')
