import os,sys,tempfile,shutil,sqlite3,datetime
from pathlib import Path
from unittest.mock import patch
from werkzeug.security import generate_password_hash
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for n in ['app.py','crm.py','leads.py','nearby.py','loyalty_qr.py','wallet.py','merchant_dashboard.py','subscriptions.py','google_identity.py','analytics.py','store_scan.py','password_recovery.py']:shutil.copy2(P/n,p/n)
 shutil.copytree(P/'static',p/'static')
 sys.path.insert(0,str(p));os.environ['TUNIBIZ_ADMIN_PASSWORD_HASH']=generate_password_hash('QA-admin-only-123')
 from app import app,db
 import google_identity
 def client():
  c=app.test_client();return c,{'X-CSRF-Token':c.get('/api/session').json['csrf']}
 def post(pair,path,body,status=200):
  c,h=pair;r=c.post('/api'+path,json=body,headers=h);assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True));return r.json
 a=client();m=client();other=client()
 params={'name':'QA Store','city':'Midoun','category':'coffee','address':'QA fixture','lat':33.88,'lon':10.86,'confirmed':True,'email':'shop@example.test','password':'QA-test-passphrase'}
 post(m,'/merchant/register',{**params,'confirmed':False},400)
 post(m,'/merchant/register',{**params,'lat':float('nan')},400)
 post(m,'/merchant/register',params,201)
 credentials={k:params[k] for k in ('email','password')}
 post(m,'/login',credentials,403)
 post(m,'/admin/shop',{'id':2,'action':'cash','reference':'QA1'},401)
 post(a,'/admin/login',{'password':'QA-admin-only-123'})
 shop=next(s for s in a[0].get('/api/admin/shops').json['shops'] if s['name']=='QA Store');sid=shop['id']
 post(a,'/admin/shop',{'id':sid,'action':'activate'},400)
 post(a,'/admin/shop',{'id':sid,'action':'cash','reference':'QA1'})
 assert post(a,'/admin/shop',{'id':sid,'action':'cash','reference':'QA1'})['duplicate']
 post(m,'/login',credentials)
 assert m[0].get('/api/crm').status_code==200
 day=datetime.date.today().isoformat()
 offer=post(m,'/nearby/offer',{'title':'QA coffee','description':'QA conditions','starts':day,'ends':day,'category':'coffee','radius':9000},201)['id']
 post(a,'/admin/shop',{'id':sid,'action':'radius','radius':2000})
 def catalog():return other[0].get('/api/nearby').json['offers']
 assert next(o for o in catalog() if o['id']==offer)['radius']==2000
 post(a,'/admin/shop',{'id':sid,'action':'offer_radius','offer_id':offer,'radius':400})
 assert next(o for o in catalog() if o['id']==offer)['radius']==400
 post(a,'/admin/shop',{'id':sid,'action':'radius','radius':10001},400)
 post(a,'/admin/shop',{'id':sid,'action':'block'})
 assert m[0].get('/api/crm').status_code==401 and not catalog()
 post(m,'/login',credentials,403)
 post(a,'/admin/shop',{'id':sid,'action':'activate'})
 post(m,'/login',credentials)
 with db() as c:
  assert c.execute('SELECT COUNT(*),SUM(amount) FROM cash_payments WHERE shop_id=?',(sid,)).fetchone()[:]==(1,19000)
  c.execute("UPDATE subscriptions SET paid_until='2000-01-01' WHERE shop_id=?",(sid,))
 assert m[0].get('/api/crm').status_code==401 and not catalog()
 print('PASS mandatory exact pin confirmation, pending, cash 19 DT idempotency, override radius, block, reactivate, expiry, role isolation')
 g=client();assert not g[0].get('/api/google/config').json['enabled'];post(g,'/google/login',{'id_token':'fake'},503)
 os.environ.update(TUNIBIZ_GOOGLE_CLIENT_ID='qa-client',TUNIBIZ_GOOGLE_CLIENT_SECRET='qa-secret',TUNIBIZ_GOOGLE_REDIRECT_URI='https://example.test/auth/google/callback')
 assert g[0].get('/auth/google/start').status_code==302
 assert g[0].get('/auth/google/callback?state=wrong&code=bad').status_code==400
 claims={'sub':'qa-subject','email':'google@example.test','name':'QA Google','email_verified':True}
 with patch.object(google_identity,'verify',side_effect=ValueError('invalid')):post(g,'/google/login',{'id_token':'bad'},401)
 # Simulate verified provider response; no claims accepted directly from client.
 with patch.object(google_identity,'verify',return_value=claims):
  post(g,'/google/login',{'id_token':'mock-verified'})
  assert g[0].get('/api/wallet').json['profile']['google_linked']
  post(g,'/wallet/logout',{})
  post(g,'/google/login',{'id_token':'mock-verified'})
  post(g,'/wallet/delete',{'password':'','confirm_google':True})
  assert g[0].get('/api/wallet').status_code==401
 print('PASS Google disabled/config guards, state rejection, invalid token, mocked verified identity/login/deletion; live OAuth not tested')
