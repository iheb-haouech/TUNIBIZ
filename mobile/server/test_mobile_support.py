"""Run with the backend dependencies installed; all SQL is in a disposable TEST database."""
from pathlib import Path
import os,sys,secrets,tempfile,time
from werkzeug.security import generate_password_hash
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='tunibiz-mobile-') as work:
 for key in list(os.environ):
  if key.startswith(('TUNIBIZ_','GOOGLE_','GMAIL_','FIREBASE_','FCM_','SMTP_')):os.environ.pop(key,None)
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET=secrets.token_hex(48),TUNIBIZ_DATA_DIR=work,TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash(secrets.token_urlsafe(32)))
 sys.path.insert(0,str(root/'mvp'))
 from app import app,db,payload,merchant,err
 from mobile_support_v060 import install
 install(app,db,payload,merchant,err)
 def post(client,path,data):
  csrf=client.get('/api/session').json['csrf'];return client.post('/api'+path,json=data,headers={'X-CSRF-Token':csrf})
 with db() as c:
  for sid in (4,5):
   c.execute('INSERT INTO shops(id,slug,name,city) VALUES(?,?,?,?)',(sid,'qa-'+str(sid),'TEST '+str(sid),'Djerba'))
   c.execute("INSERT INTO subscriptions(shop_id,status,paid_until,category) VALUES(?,'active','2099-01-01','grocery')",(sid,))
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'qa'+str(sid)+'@example.test',generate_password_hash('QA-mobile-support!')))
 guest=app.test_client();assert guest.get('/api/mobile/business/scans').status_code==401
 assert guest.get('/api/mobile/capabilities').json['features']['scan_history']
 assert guest.get('/api/mobile/partners').json['stores']==[]
 os.environ['TUNIBIZ_PUBLIC_PARTNER_SLUGS']='qa-4'
 assert [r['id'] for r in guest.get('/api/mobile/partners').json['stores']]==[4]
 client=app.test_client();assert post(client,'/wallet/register',{'name':'TEST','email':'native@example.test','password':'QA-mobile-support!'}).status_code==201
 with db() as c:c.execute('UPDATE consumer_accounts SET email_verified=1')
 for slug in ('qa-4','qa-5'):assert post(client,'/wallet/store-scan',{'slug':slug}).status_code==201
 scans={}
 for slug in ('qa-4','qa-5'):scans[slug]=post(client,'/wallet/store-scan',{'slug':slug}).json['id']
 business=app.test_client();assert post(business,'/login',{'email':'qa4@example.test','password':'QA-mobile-support!'}).status_code==200
 other=app.test_client();assert post(other,'/login',{'email':'qa5@example.test','password':'QA-mobile-support!'}).status_code==200
 assert post(business,'/crm/store-scan/decide',{'id':scans['qa-4'],'action':'approve','points':5}).status_code==200
 rows=business.get('/api/mobile/business/scans?shop_id=5').json['requests'];assert len(rows)==1 and rows[0]['id']==scans['qa-4'] and rows[0]['state']=='approved'
 assert other.get('/api/mobile/business/scans').json['requests'][0]['id']==scans['qa-5']
 assert business.get('/api/mobile/business/scans?state=approved').json['requests'][0]['points']==5
 assert business.get('/api/mobile/business/scans?cursor=bad').status_code==400
 assert business.get('/api/mobile/business/scans?limit=999').status_code==400
 assert post(business,'/mobile/business/category',{'category':'coffee','category_detail':''}).status_code==200
 assert post(business,'/mobile/business/category',{'category':'other','category_detail':''}).status_code==400
 assert post(business,'/mobile/business/category',{'category':'coffee','shop_id':5}).status_code==400
 with db() as c:
  assert c.execute('SELECT category FROM subscriptions WHERE shop_id=4').fetchone()[0]=='coffee'
  assert c.execute('SELECT category FROM subscriptions WHERE shop_id=5').fetchone()[0]=='grocery'
  old=scans['qa-5'];c.execute('UPDATE store_scan_requests SET expires=? WHERE id=?',(int(time.time())-1,old))
 assert other.get('/api/mobile/business/scans?state=expired').json['requests'][0]['id']==old
 with db() as c:assert c.execute('SELECT state FROM store_scan_requests WHERE id=?',(old,)).fetchone()[0]=='pending'
 # Cursor pagination remains scoped and does not lose rows with identical timestamps.
 with db() as c:
  row=c.execute('SELECT * FROM store_scan_requests WHERE id=?',(scans['qa-4'],)).fetchone()
  for ident in ('page-a','page-b'):
   c.execute("INSERT INTO store_scan_requests(id,account_id,shop_id,customer_id,created,expires,state) VALUES(?,?,?,?,?,?,'expired')",(ident,row['account_id'],4,row['customer_id'],row['created'],row['expires']))
 seen=[];cursor=''
 for _ in range(4):
  result=business.get('/api/mobile/business/scans?limit=1'+('&cursor='+cursor if cursor else '')).json
  seen += [r['id'] for r in result['requests']];cursor=result['next_cursor']
  if not cursor:break
 assert len(seen)==3 and len(set(seen))==3 and scans['qa-5'] not in seen
 print('PASS: read-only scoped scan history, state filters, cursor pagination, category ownership, explicit public-partner authorization; no migration')
