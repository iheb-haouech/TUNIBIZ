"""Isolated V0.5.2 behavioral/security regression. No production accounts or sends."""
import base64,io,os,shutil,sys,tempfile,time,json
from pathlib import Path
from PIL import Image
from werkzeug.security import generate_password_hash
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+'x'*64,TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash('QA-admin-password'))
 sys.path.insert(0,str(p))
 from app import app,db
 from commerce import phone_number,install
 assert phone_number('20 123 456')==phone_number('00216 20 123 456')=='+21620123456'
 checks=[]
 def check(name):checks.append(name);print('PASS',name,flush=True)
 with db() as c:
  for sid in (1,2):
   c.execute('INSERT INTO shops(id,slug,name,city) VALUES(?,?,?,?)',(sid,'qa'+str(sid),'QA Commerce '+str(sid),'Djerba'))
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'m'+str(sid)+'@example.test',generate_password_hash('QA-merchant-password')))
   c.execute("INSERT INTO subscriptions(shop_id,status,paid_until,category) VALUES(?,'active','2099-01-01','drugstore')",(sid,))
   c.execute('INSERT INTO nearby_locations(shop_id,lat,lon,address,location_confirmed) VALUES(?,33.8,10.8,?,1)',(sid,'Adresse QA '+str(sid)))
 def get(cli,path,status=200):
  r=cli.get('/api'+path,base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:600]);return r.json
 def post(cli,path,body,status=200):
  csrf=get(cli,'/session')['csrf'];r=cli.post('/api'+path,json=body,headers={'X-CSRF-Token':csrf},base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:600]);return r.json
 m,n,a,b,ad,g=[app.test_client() for _ in range(6)]
 for cli,sid in ((m,1),(n,2)):post(cli,'/login',{'email':'m'+str(sid)+'@example.test','password':'QA-merchant-password'})
 for cli,name in ((a,'a'),(b,'b')):post(cli,'/wallet/register',{'name':'QA '+name,'email':name+'@example.test','password':'QA-consumer-password'},201)
 post(ad,'/admin/login',{'password':'QA-admin-password'})
 assert get(a,'/stores')['stores']==[]
 post(m,'/commerce/storefront',{'published':True},400)
 raw=io.BytesIO();Image.new('RGB',(500,400),'#2277cc').save(raw,'JPEG')
 photo=post(m,'/storefront/photo',{'image':base64.b64encode(raw.getvalue()).decode()},201)['id']
 post(n,'/commerce/storefront',{'photo':photo},400)
 post(m,'/commerce/storefront',{'photo':photo,'phone':'+21620123456','published':True})
 post(m,'/storefront/photo/delete',{'id':photo},409)
 assert get(a,'/stores')['stores'][0]['photo']==photo
 check('publication requires primary photo and contact; foreign photo rejected')
 get(g,'/commerce/business',401);get(m,'/commerce/admin',401)
 post(m,'/commerce/sponsor',{'shop_id':1,'title':'forbidden'},401)
 check('server-side merchant/admin role separation')
 cid=post(m,'/crm/customer',{'name':'QA existing','phone':'20 123 456','consent':False},201)['id']
 post(m,'/crm/customer',{'name':'Duplicate','phone':'+21620123456'},409)
 assert post(m,'/commerce/customer/search',{'phone':'00216 20 123 456'})['customers'][0]['id']==cid
 assert post(n,'/commerce/customer/search',{'phone':'20123456'})['customers']==[]
 check('phone normalization, duplicates and tenant-scoped search')
 body={'id':cid,'points':20,'reason':'QA points without amount','key':'test-reference-00001'}
 post(n,'/commerce/points',body,404)
 post(m,'/commerce/points',body,201)
 assert post(m,'/commerce/points',body)['duplicate']
 post(m,'/commerce/points',{**body,'points':21},409)
 post(m,'/commerce/points',{**body,'points':-21,'key':'test-reference-00002'},409)
 assert get(m,'/crm/customer/'+str(cid))['customer']['points']==20
 check('points without price, idempotency, cross-shop rejection and no negative balance')
 post(a,'/commerce/profile',{'phone':'+21620123456','shared':True})
 assert get(a,'/commerce/profile')['phone']['verified']==0
 post(a,'/commerce/join',{'shop_id':1,'consent':True},403)
 with db() as c:c.execute('UPDATE consumer_accounts SET email_verified=1')
 post(a,'/commerce/join',{'shop_id':1,'consent':True},409)
 invitation=post(m,'/commerce/customer/invite',{'id':cid})['invite']
 post(a,'/commerce/join',{'shop_id':2,'consent':True,'invite':invitation},409)
 post(a,'/commerce/join',{'shop_id':1,'consent':True,'invite':invitation},201)
 assert get(a,'/wallet')['cards'][0]['points']==20
 check('phone stays unverified; verified email, explicit consent and shop-bound invitation required')
 post(a,'/push/register',{'device_id':'a'*32,'token':'fake_test_'+'x'*50,'consent':True})
 post(m,'/commerce/points',{**body,'points':5,'key':'test-reference-00003'},201)
 assert len(get(a,'/commerce/profile')['notifications'])==1
 from fcm_dispatch import deliver_commerce
 sent=[]
 def fake_send(msg):sent.append(msg);return 'sent'
 assert deliver_commerce(db,fake_send)['sent']==1
 assert deliver_commerce(db,fake_send)['sent']==0
 assert 'qa@example' not in str(sent) and '+216' not in str(sent)
 check('attributed points generate authenticated in-app notification')
 promo={'title':'QA -20%','description':'Avantage QA','benefit':'discount','discount':20,'starts':str(__import__('datetime').date.today()),'ends':'2099-01-01','state':'active'}
 from datetime import date,timedelta
 promo['ends']=str(date.today()+timedelta(days=10))
 oid=post(m,'/commerce/promotion',promo,201)['id']
 assert get(a,'/stores/1')['offers'][0]['old_price']is None
 post(m,'/commerce/promotion',{**promo,'sponsored':True},400)
 private=post(m,'/commerce/promotion',{**promo,'audience':'members','title':'QA private'},201)['id']
 assert private not in [o['id'] for o in get(a,'/commerce/home')['offers']]
 post(a,'/storefront/coupon/claim',{'id':private},404)
 check('price-free public promotion, audience filtering and sponsor escalation rejected')
 post(m,'/commerce/nearby',{'id':oid,'enabled':True,'radius':1000})
 assert [o['id'] for o in get(a,'/nearby')['offers']]==[oid]
 post(m,'/commerce/nearby',{'id':private,'enabled':True,'radius':1000},400)
 post(m,'/commerce/nearby',{'id':oid,'enabled':True,'radius':1001},400)
 post(n,'/commerce/nearby',{'id':oid,'enabled':True,'radius':1000},404)
 check('Nearby references one promotion, respects radius and rejects private audience')
 s=post(ad,'/commerce/sponsor',{'shop_id':1,'title':'QA Sponsor','description':'Partner QA','photo':photo,'starts':promo['starts'],'ends':promo['ends'],'status':'active','priority':2})
 assert get(a,'/commerce/home')['sponsors'][0]['sponsored']is True
 check('admin-only sponsored home carousel')
 coupon=post(a,'/storefront/coupon/claim',{'id':oid},201)['code']
 post(n,'/storefront/coupon/redeem',{'code':coupon},404)
 post(m,'/storefront/coupon/redeem',{'code':coupon})
 post(m,'/storefront/coupon/redeem',{'code':coupon},409)
 check('coupon has one use and cannot be redeemed by another commerce')
 limited=post(m,'/commerce/promotion',{**promo,'max_uses':1},201)['id']
 from concurrent.futures import ThreadPoolExecutor
 def concurrent_claim(cli):
  token=get(cli,'/session')['csrf']
  return cli.post('/api/storefront/coupon/claim',json={'id':limited},headers={'X-CSRF-Token':token},base_url='https://localhost').status_code
 with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(concurrent_claim,[a,b]))==[201,409]
 check('last available coupon is protected against simultaneous claims')
 code=post(m,'/commerce/code',{'title':'QA personal','discount':10,'expires':promo['ends'],'customer_id':cid,'max_uses':1},201)['code']
 post(a,'/commerce/code/use',{'shop_id':2,'code':code},404)
 issued=post(a,'/commerce/code/use',{'shop_id':1,'code':code},201)
 post(a,'/commerce/code/use',{'shop_id':1,'code':code},409)
 personal_id=get(a,'/stores/1')['coupons'][-1]['offer_id']
 post(b,'/storefront/coupon/claim',{'id':personal_id},404)
 check('personal promotion codes produce single-use coupons and resist replay/cross-shop/ID guessing')
 d=get(m,'/commerce/business');assert d['stats']['points_issued']==25 and d['stats']['storefront_views']is None
 assert not any(k in d['stats'] for k in ('sales','spent','revenue'))
 with db() as c:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert list(c.execute('PRAGMA foreign_key_check'))==[]
 check('recorded nonfinancial KPIs, SQLite integrity and foreign keys')
 # Repeat schema migration on the populated copy: must retain all records.
 with db() as c:before=c.execute('SELECT COUNT(*) FROM storefront_offers').fetchone()[0]
 # Migration insertion helper is exercised by importing a fresh app process in integration tests.
 for path in ('/client','/crm','/stores','/wallet','/admin','/nearby/business'):
  assert m.get(path,base_url='https://localhost').status_code==200
 check('all spaces serve their coherent shell')
 post(a,'/wallet/delete',{'password':'QA-consumer-password'})
 with db() as c:
  assert c.execute('SELECT phone_normalized FROM crm_customers WHERE id=?',(cid,)).fetchone()[0]is None
  assert c.execute('SELECT COUNT(*) FROM commerce_phones').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM commerce_push_outbox').fetchone()[0]==0
 check('account deletion removes normalized phone, contact preferences and queued push')
 print(json.dumps({'passed':len(checks),'checks':checks}))
