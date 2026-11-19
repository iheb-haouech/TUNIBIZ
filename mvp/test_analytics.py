import os,sys,tempfile,shutil
from pathlib import Path
from werkzeug.security import generate_password_hash
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for n in ['app.py','crm.py','leads.py','nearby.py','loyalty_qr.py','wallet.py','merchant_dashboard.py','subscriptions.py','google_identity.py','analytics.py','store_scan.py','app_release.py','storefront.py','password_recovery.py']:shutil.copy2(P/n,p/n)
 shutil.copytree(P/'static',p/'static')
 sys.path.insert(0,str(p));os.environ['TUNIBIZ_ADMIN_PASSWORD_HASH']=generate_password_hash('QA-admin-only-123');os.environ.pop('TUNIBIZ_GA4_MEASUREMENT_ID',None)
 from app import app,db
 visitor=app.test_client();admin=app.test_client();csrf=visitor.get('/api/session').json['csrf'];h={'X-CSRF-Token':csrf}
 opt={**h,'X-Tunibiz-Analytics':'yes','X-Tunibiz-Platform':'android'}
 assert visitor.get('/api/admin/overview').status_code==401
 assert visitor.get('/api/admin/consumers').status_code==401
 assert visitor.get('/api/analytics/config').json['measurement_id']==''
 assert visitor.get('/api/nearby').status_code==200
 assert visitor.post('/api/analytics/event',json={'event':'home_view'},headers=h).status_code==403
 assert visitor.post('/api/analytics/event',json={'event':'home_view','gps':'secret'},headers=opt).status_code==400
 assert visitor.post('/api/analytics/event',json={'event':'alice@example.test'},headers=opt).status_code==400
 assert visitor.get('/api/nearby',headers=opt).headers['X-Tunibiz-Event']=='nearby_catalog'
 assert visitor.post('/api/analytics/event',json={'event':'home_view'},headers=opt).status_code==200
 assert visitor.post('/api/wallet/register',json={'email':'qa@example.test','name':'QA Person','password':'QA-long-password'},headers=h).status_code==201
 assert visitor.get('/api/wallet').status_code==200
 assert visitor.get('/api/wallet',headers=opt).headers['X-Tunibiz-Event']=='wallet_view'
 admincsrf=admin.get('/api/session').json['csrf'];assert admin.post('/api/admin/login',json={'password':'QA-admin-only-123'},headers={'X-CSRF-Token':admincsrf}).status_code==200
 d=admin.get('/api/admin/overview').json
 assert d['business']['consumers']==1 and d['business']['wallet_sessions']==1
 assert {r['event']:r['count'] for r in d['events']}=={'home_view':1,'nearby_catalog':1,'wallet_view':1},d
 a=admin.get('/api/admin/consumers').json['accounts'];assert len(a)==1 and a[0]['email']=='qa@example.test' and 'password' not in a[0]
 assert admin.get('/api/admin/consumers?offset=50').json['accounts']==[]
 with db() as c:
  cols={r['name'] for r in c.execute('PRAGMA table_info(analytics_daily)')};assert cols=={'day','platform','event','n'}
 print('PASS anonymous opt-in aggregates, rejection of unsolicited data, central business records independent of consent, admin access and pagination')
