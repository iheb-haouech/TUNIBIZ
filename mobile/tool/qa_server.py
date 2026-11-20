"""Local Android acceptance server. Isolated TEST data; never loads production configuration."""
import os,sys,time,secrets,hashlib
from pathlib import Path
from datetime import date,timedelta
from werkzeug.security import generate_password_hash
root=Path(__file__).resolve().parents[2]
data=Path('E:/TUNIBIZ-Dev/v060')/('qa-'+str(int(time.time())))
data.mkdir()
for key in list(os.environ):
 if key.startswith(('TUNIBIZ_','GOOGLE_','GMAIL_','FIREBASE_','FCM_','SMTP_')):os.environ.pop(key,None)
os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET=secrets.token_hex(48),TUNIBIZ_DATA_DIR=str(data),TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash(secrets.token_urlsafe(32)))
sys.path.insert(0,str(root/'mvp'))
from app import app,db
from qa_support import publish_fixture
from flask import request,jsonify
app.config.update(SESSION_COOKIE_SECURE=False)
@app.get('/__qa__/state')
def state():
 with db() as c:
  return jsonify(cards=[dict(r) for r in c.execute('SELECT id,shop_id,name FROM crm_customers')],scans=[dict(r) for r in c.execute('SELECT * FROM store_scan_requests')],offers=[dict(r) for r in c.execute('SELECT id,shop_id,title FROM storefront_offers')])
@app.post('/__qa__/verification')
def confirmation_fixture():
 email=(request.json or {}).get('email');token=secrets.token_urlsafe(32)
 with db() as c:
  row=c.execute('SELECT id FROM consumer_accounts WHERE email=?',(email,)).fetchone()
  if not row:return jsonify(error='TEST account missing'),404
  c.execute('INSERT INTO email_confirmations VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],int(time.time())+1200))
 return jsonify(token=token)
with db() as c:
 for sid,slug,name in [(4,'cd8f57567e0a88135bf84f51','المخزن الجربي — TEST'),(5,'qa-second','Café de recette — TEST')]:
  c.execute('INSERT INTO shops(id,slug,name,city) VALUES(?,?,?,?)',(sid,slug,name,'Djerba'))
  c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'merchant.qa@example.test' if sid==4 else 'other.qa@example.test',generate_password_hash('QA-Merchant-060!')))
  c.execute("INSERT INTO subscriptions(shop_id,status,paid_until,category) VALUES(?,'active','2099-01-01',?)",(sid,'grocery' if sid==4 else 'coffee'))
for sid in (4,5):publish_fixture(db,sid)
with db() as c:c.execute('UPDATE storefront_profiles SET published=0 WHERE shop_id=4')
def post(cli,path,body):
 csrf=cli.get('/api/session').json['csrf']
 r=cli.post('/api'+path,json=body,headers={'X-CSRF-Token':csrf})
 assert r.status_code in (200,201),(path,r.status_code,r.get_data(as_text=True))
 return r.json
customer=app.test_client()
post(customer,'/wallet/register',dict(name='Client QA TEST',email='client.qa@example.test',password='QA-Client-060!'))
with db() as c:c.execute('UPDATE consumer_accounts SET email_verified=1')
for sid,slug,extra in [(4,'cd8f57567e0a88135bf84f51',47),(5,'qa-second',4)]:
 post(customer,'/wallet/store-scan',{'slug':slug})
 card=next(x for x in customer.get('/api/wallet').json['cards'] if x['shop_id']==sid)
 merchant=app.test_client()
 post(merchant,'/login',{'email':'merchant.qa@example.test' if sid==4 else 'other.qa@example.test','password':'QA-Merchant-060!'})
 post(merchant,'/commerce/points',{'id':card['id'],'points':extra,'reason':'Solde de recette TEST','key':secrets.token_hex(20)})
 with db() as c:c.execute('UPDATE crm_customers SET phone=?,phone_normalized=? WHERE id=?',('+21620123456','+21620123456',card['id']))
 post(merchant,'/commerce/reward',{'title':'Avantage de recette TEST','cost':100,'description':'Données de recette isolées','visual':'gift'})
 if sid==5:
  post(merchant,'/commerce/promotion',{'title':'Cadeau découverte TEST','description':'Recette Android','benefit':'gift','starts':str(date.today()),'ends':str(date.today()+timedelta(days=10)),'state':'active'})
print('TEST SERVER',data,flush=True)
app.run(host='127.0.0.1',port=8879,threaded=True,use_reloader=False)
