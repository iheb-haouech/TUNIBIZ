"""Isolated admin pilot regression: authorization, audit atomicity, cash and moderation."""
import os,sys,tempfile,shutil,io,base64
from pathlib import Path
from datetime import datetime,timezone,timedelta
from werkzeug.security import generate_password_hash
from PIL import Image
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_REQUIRE_EMAIL_VERIFICATION='0',TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+('x'*64),TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash('QA-admin-passphrase'))
 sys.path.insert(0,str(p))
 from app import app,db
 clients=[app.test_client() for _ in range(4)]
 a,m,n,u=clients
 def get(c,path,status=200):
  r=c.get('/api'+path,base_url='https://localhost')
  assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:150]);return r
 def post(c,path,body,status=200):
  h={'X-CSRF-Token':get(c,'/session').json['csrf']}
  r=c.post('/api'+path,json=body,headers=h,base_url='https://localhost')
  assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:150]);return r.json
 def count():
  with db() as c:return c.execute('SELECT COUNT(*) FROM admin_operations').fetchone()[0]
 get(u,'/admin/history',401);get(u,'/admin/moderation',401);get(u,'/admin/photo/'+'a'*32,401)
 post(a,'/admin/login',{'password':'QA-admin-passphrase'})
 ids=[]
 for client,slug in ((m,'first'),(n,'second')):
  post(client,'/merchant/register',{'name':slug,'city':'Midoun','category':'coffee','address':'QA only','lat':33.88,'lon':10.86,'confirmed':True,'email':slug+'@example.test','password':'QA-merchant-passphrase'},201)
 ids=[s['id'] for s in get(a,'/admin/shops').json['shops']]
 sid=next(s['id'] for s in get(a,'/admin/shops').json['shops'] if s['name']=='first')
 sid2=next(s['id'] for s in get(a,'/admin/shops').json['shops'] if s['name']=='second')
 profile={'id':sid,'action':'profile','name':'QA <script>','city':'Houmt Souk','category':'other','category_detail':''}
 before=count()
 post(m,'/admin/shop',profile,401)
 post(a,'/admin/shop',profile,400)
 assert count()==before
 post(a,'/admin/shop',{**profile,'category_detail':'Artisanat'})
 shop=next(s for s in get(a,'/admin/shops').json['shops'] if s['id']==sid)
 assert shop['name']=='QA <script>' and shop['category_detail']=='Artisanat' and shop['category']=='other'
 for invalid in ({'category':'unrecognized'},{'name':True},{'city':{}},{'category_detail':['bad']}):
  post(a,'/admin/shop',{**profile,'category_detail':'Artisanat',**invalid},400)
 cash={'id':sid,'action':'cash','reference':'QA-pilot-receipt'}
 post(a,'/admin/shop',cash)
 before=count();assert post(a,'/admin/shop',cash)['duplicate'];assert count()==before
 post(a,'/admin/shop',{**cash,'id':sid2},409)
 overview=get(a,'/admin/overview').json
 assert overview['business']['active_shops']==1 and overview['business']['pending_shops']==1
 assert overview['business']['monthly_cash_millimes']==19000 and overview['monthly_cash'][0]['amount_millimes']==19000
 history=get(a,'/admin/history').json
 assert len(history['payments'])==1 and history['payments'][0]['reference']=='QA-pilot-receipt'
 assert {'login','profile','cash'}<={r['action'] for r in history['operations']}
 get(a,'/admin/history?offset=-1',400)
 post(m,'/login',{'email':'first@example.test','password':'QA-merchant-passphrase'})
 from qa_support import publish_fixture
 publish_fixture(db,sid)
 day=datetime.now(timezone(timedelta(hours=1))).date().isoformat()
 offer=post(m,'/nearby/offer',{'title':'QA nearby','description':'Conditions QA','starts':day,'ends':day,'category':'coffee'},201)['id']
 mod={'id':sid,'action':'moderate_offer','kind':'nearby','offer_id':offer,'active':False}
 post(a,'/admin/shop',{**mod,'id':sid2},404)
 post(m,'/admin/shop',mod,401)
 post(a,'/admin/shop',mod)
 assert get(u,'/nearby').json['offers']==[]
 post(a,'/admin/shop',{**mod,'active':True})
 assert len(get(u,'/nearby').json['offers'])==1
 im=Image.new('RGB',(16,16),'blue');b=io.BytesIO();im.save(b,'JPEG')
 photo=post(m,'/storefront/photo',{'image':base64.b64encode(b.getvalue()).decode()},201)['id']
 get(a,'/admin/photo/'+photo)
 hidden={'id':sid,'action':'moderate_photo','photo_id':photo,'hidden':True}
 post(a,'/admin/shop',{**hidden,'id':sid2},404)
 post(a,'/admin/shop',hidden)
 assert any('photo_id' in x['details'] for x in get(a,'/admin/history').json['operations'] if x['action']=='moderate_photo')
 photos=get(a,'/admin/moderation?shop_id='+str(sid)).json['photos']
 assert next(p for p in photos if p['id']==photo)['hidden']==1
 post(a,'/admin/shop',{**hidden,'hidden':False})
 assert get(a,'/admin/moderation?shop_id='+str(sid)).json['photos'][0]['hidden']==0
 # The journal write is in the mutation transaction: an audit failure must roll back.
 before=count()
 with db() as c:c.execute("CREATE TRIGGER qa_fail_audit BEFORE INSERT ON admin_operations BEGIN SELECT RAISE(ABORT,'qa'); END")
 old=next(s for s in get(a,'/admin/shops').json['shops'] if s['id']==sid)['name']
 app.logger.disabled=True
 post(a,'/admin/shop',{**profile,'name':'Must roll back','category_detail':'Artisanat'},500)
 assert count()==before and next(s for s in get(a,'/admin/shops').json['shops'] if s['id']==sid)['name']==old
 with db() as c:c.execute('DROP TRIGGER qa_fail_audit')
 post(a,'/admin/logout',{})
 get(a,'/admin/history',401)
 print('PASS admin roles, validated editing, unique cash receipts, real monthly/status totals, durable atomic journal, scoped offer/photo moderation and logout')
