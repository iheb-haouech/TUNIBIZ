"""Isolated campaign artwork and nearby catalogue regression."""
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
  c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'merchant@example.test',generate_password_hash('Test-merchant-password')))
  c.execute("INSERT INTO subscriptions(shop_id,status,paid_until,radius,category) VALUES(?,'active','2099-01-01',500,'restaurant')",(sid,))
 a=app.test_client()
 def get(path):return a.get('/api'+path,base_url='https://localhost')
 def post(path,body,status=200):
  r=a.post('/api'+path,json=body,headers={'X-CSRF-Token':get('/session').json['csrf']},base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.json);return r.json
 post('/login',{'email':'merchant@example.test','password':'Test-merchant-password'})
 campaign={'title':'QA offer','description':'Test conditions','segment':'all','starts':'2020-01-01','ends':'2099-01-01'}
 post('/crm/campaign',{**campaign,'visual':'https://evil.example/a.png'},400)
 cid=post('/crm/campaign',{**campaign,'visual':'restaurant'},201)['id']
 old=post('/crm/campaign',campaign,201)['id']
 d=get('/crm').json
 assert d['dashboard']['shop']['category']=='restaurant'
 assert {x['id']:x['visual'] for x in d['campaigns']}=={cid:'restaurant',old:'general'}
 post('/nearby/location',{'lat':33.88,'lon':10.86,'address':'QA'})
 oid=post('/nearby/offer',{**campaign,'category':'coffee'},201)['id']
 assert get('/nearby/business').json['offers'][0]['category']=='coffee'
 assert get('/nearby').json['offers'][0]['category']=='coffee'
 post('/nearby/stop',{'id':oid})
 assert get('/nearby').json['offers']==[]
 print('PASS persistent campaign visual, existing default, validated artwork selection, real merchant category, Nearby photo category and stop')
