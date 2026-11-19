"""Archive safely: authorization, revocation, preserved history and explicit restoration."""
import os,sys,tempfile,shutil
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
  sid=c.execute("INSERT INTO shops(slug,name,city) VALUES('qa','QA','Test')").lastrowid
  c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'qa@example.test',generate_password_hash('Test-merchant-password')))
  c.execute("INSERT INTO subscriptions(shop_id,status,paid_until) VALUES(?,'active','2099-01-01')",(sid,))
  c.execute("INSERT INTO nearby_locations(shop_id,lat,lon,address,location_confirmed) VALUES(?,33.88,10.86,'QA',1)",(sid,))
  c.execute("INSERT INTO cash_payments(shop_id,reference,amount) VALUES(?,'qa-original',19000)",(sid,))
 a,m,u=app.test_client(),app.test_client(),app.test_client()
 def get(c,path,status=200):
  r=c.get(path,base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.json);return r
 def post(c,path,body,status=200):
  r=c.post('/api'+path,json=body,headers={'X-CSRF-Token':get(c,'/api/session').json['csrf']},base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.json);return r.json
 post(a,'/admin/login',{'password':'Test-admin-password'})
 post(m,'/login',{'email':'qa@example.test','password':'Test-merchant-password'})
 post(u,'/wallet/register',{'name':'QA Customer','email':'wallet@example.test','password':'Test-consumer-password'},201)
 post(u,'/wallet/store-scan',{'slug':'qa'},201)
 post(u,'/wallet/store-scan',{'slug':'qa'},201)
 archive={'id':sid,'action':'archive','confirm':True}
 post(m,'/admin/shop',archive,401)
 post(a,'/admin/shop',{'id':sid,'action':'archive'},400)
 post(a,'/admin/shop',archive)
 assert post(a,'/admin/shop',archive)['duplicate']
 assert get(a,'/api/admin/shops').json['shops'][0]['status']=='archived'
 assert get(u,'/api/stores').json['stores']==[]
 get(u,'/join/qa',404);get(u,'/api/stores/'+str(sid),404)
 get(m,'/api/crm',401)
 post(m,'/login',{'email':'qa@example.test','password':'Test-merchant-password'},403)
 card=get(u,'/api/wallet').json['cards'][0];assert card['points']==3 and card['archived']==1 and card['eligible']==0
 for action in ('activate','cash','block','radius','offer_radius'):post(a,'/admin/shop',{'id':sid,'action':action},409)
 with db() as c:
  assert c.execute('SELECT SUM(amount) FROM cash_payments').fetchone()[0]==19000
  assert c.execute("SELECT state FROM store_scan_requests").fetchone()[0]=='expired'
  assert c.execute('SELECT COUNT(*) FROM merchant_sessions').fetchone()[0]==0
 post(a,'/admin/shop',{'id':sid,'action':'restore','confirm':True})
 assert get(a,'/api/admin/shops').json['shops'][0]['status']=='blocked'
 assert get(u,'/api/stores').json['stores']==[]
 post(a,'/admin/shop',{'id':sid,'action':'activate'})
 assert len(get(u,'/api/stores').json['stores'])==1
 assert get(u,'/api/wallet').json['cards'][0]['points']==3
 print('PASS admin-only archive, explicit confirmation, revocation, preserved cash and points, no accidental reactivation, blocked restoration')
