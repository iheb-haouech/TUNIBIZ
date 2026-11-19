"""Storefront active directory, ownership, real images, dated offers and one-use coupons."""
import os,sys,tempfile,shutil,io,base64
from pathlib import Path
from PIL import Image
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
 ids={}
 with db() as c:
  for slug in ('first','second','blocked'):
   sid=c.execute('INSERT INTO shops(slug,name,city) VALUES(?,?,?)',(slug,slug,'Test')).lastrowid
   ids[slug]=sid
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,slug+'@example.test',generate_password_hash('Test-merchant-password')))
   c.execute('INSERT INTO subscriptions(shop_id,status,paid_until,category) VALUES(?,?,?,?)',(sid,'blocked' if slug=='blocked' else 'active','2099-01-01','restaurant'))
 def get(a,path,status=200):
  r=a.get(path,base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:300]);return r
 def post(a,path,data,status=200):
  r=a.post('/api'+path,json=data,headers={'X-CSRF-Token':get(a,'/api/session').json['csrf']},base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:300]);return r.json
 m,n,a,b=app.test_client(),app.test_client(),app.test_client(),app.test_client()
 for client,slug in ((m,'first'),(n,'second')):post(client,'/login',{'email':slug+'@example.test','password':'Test-merchant-password'})
 for client,email in ((a,'a'),(b,'b')):post(client,'/wallet/register',{'name':'QA '+email,'email':email+'@example.test','password':'Test-consumer-password'},201)
 assert {r['id'] for r in get(a,'/api/stores').json['stores']}=={ids['first'],ids['second']}
 get(a,'/api/stores/'+str(ids['blocked']),404)
 post(a,'/wallet/store-scan',{'slug':'first'},201)
 assert [r['joined'] for r in get(a,'/api/stores').json['stores']]==[True,False]
 assert get(a,'/api/wallet').json['cards'][0]['shop_id']==ids['first']
 post(a,'/storefront/photo',{'image':'bogus'},401)
 post(m,'/storefront/photo',{'image':'bogus'},400)
 im=Image.effect_noise((512,512),80).convert('RGB');buf=io.BytesIO();im.save(buf,'JPEG',quality=90)
 raw=base64.b64encode(buf.getvalue()).decode()
 assert len(raw)>32768
 photo=post(m,'/storefront/photo',{'image':raw},201)['id']
 get(a,'/media/store/'+photo,404)
 post(n,'/storefront/profile',{'description':'No','cover':photo},400)
 post(m,'/storefront/profile',{'description':'Une vraie vitrine','cover':photo})
 assert get(a,'/media/store/'+photo).mimetype=='image/jpeg'
 post(m,'/storefront/photo/delete',{'id':photo},409)
 base={'kind':'pack','title':'Pack QA','description':'Deux produits, conditions en caisse','starts':'2026-01-01','ends':'2026-12-31','old_price':20000,'new_price':15000,'photo':photo}
 # The tests use actual host date; construct relative dates instead of a hardcoded scenario.
 from datetime import date,timedelta
 today=date.today();base.update(starts=today.isoformat(),ends=(today+timedelta(days=10)).isoformat())
 pack=post(m,'/storefront/offer',base,201)['id']
 post(m,'/storefront/offer',{**base,'new_price':25000},400)
 post(n,'/storefront/offer',base,400)
 future=post(m,'/storefront/offer',{**base,'starts':(today+timedelta(days=1)).isoformat()},201)['id']
 past=post(m,'/storefront/offer',{**base,'starts':(today-timedelta(days=10)).isoformat(),'ends':(today-timedelta(days=1)).isoformat()},201)['id']
 coupon=post(m,'/storefront/offer',{**base,'kind':'coupon','title':'Coupon QA','discount':15},201)['id']
 view=get(a,'/api/stores/'+str(ids['first'])).json
 assert {x['id'] for x in view['offers']}=={pack,coupon} and view['cover']==photo
 ah={'X-CSRF-Token':get(a,'/api/session').json['csrf'],'X-Tunibiz-Analytics':'yes','X-Tunibiz-Platform':'web'}
 first=a.post('/api/storefront/coupon/claim',json={'id':coupon},headers=ah,base_url='https://localhost')
 assert first.status_code==201 and first.headers['X-Tunibiz-Event']=='coupon_claimed'
 code=first.json['code']
 again=a.post('/api/storefront/coupon/claim',json={'id':coupon},headers=ah,base_url='https://localhost')
 assert again.status_code==200 and again.json['code']==code and again.json['duplicate'] is True
 assert 'X-Tunibiz-Event' not in again.headers
 with db() as c:assert c.execute("SELECT SUM(n) FROM analytics_daily WHERE platform='web' AND event='coupon_claimed'").fetchone()[0]==1
 assert post(b,'/storefront/coupon/claim',{'id':coupon},201)['code']!=code
 assert get(b,'/api/stores/'+str(ids['first'])).json['coupons'][0]['code']!=code
 post(n,'/storefront/coupon/redeem',{'code':code},404)
 assert post(m,'/storefront/coupon/redeem',{'code':code})['discount']==15
 post(m,'/storefront/coupon/redeem',{'code':code},409)
 post(m,'/storefront/stop',{'id':pack})
 assert pack not in [o['id'] for o in get(a,'/api/stores/'+str(ids['first'])).json['offers']]
 with db() as c:c.execute("UPDATE subscriptions SET status='blocked' WHERE shop_id=?",(ids['first'],))
 get(a,'/api/stores/'+str(ids['first']),404)
 get(a,'/media/store/'+photo,404)
 post(a,'/storefront/coupon/claim',{'id':coupon},404)
 get(m,'/api/storefront/manage',401)
 assert len(get(a,'/api/stores').json['stores'])==1
 assert get(a,'/stores').status_code==200 and get(m,'/storefront').status_code==200
 print('PASS active directory, joined flag, verified PNG/JPEG processing, private ownership, dated pack/promo, coupon single-use and isolation, block and stop')
