"""Version authorization, monotonicity and consistent backup."""
import os,sys,tempfile,shutil,sqlite3
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
 from app import app
 from backup_db import backup
 a,b=app.test_client(),app.test_client()
 def get(client,path):
  return client.get('/api'+path,base_url='https://localhost')
 def headers(client):
  return {'X-CSRF-Token':get(client,'/session').json['csrf']}
 ha,hb=headers(a),headers(b)
 def post(client,h,path,data,status):
  r=client.post('/api'+path,headers=h,json=data,base_url='https://localhost');assert r.status_code==status,(r.status_code,r.json);return r
 release={'version':'0.4.2','code':6,'url':'https://github.com/iheb-haouech/TUNIBIZ/releases/download/v0.4.2/TUNIBIZ-v0.4.2.apk','sha256':'a'*64,'notes':'QA fixture','verified':True}
 assert get(a,'/app/version').json['release'] is None
 post(b,hb,'/admin/app-release',release,401)
 post(a,ha,'/admin/login',{'password':'Test-admin-password'},200)
 post(a,ha,'/admin/app-release',{**release,'url':'https://example.test/a.apk'},400)
 post(a,ha,'/admin/app-release',{**release,'verified':False},400)
 post(a,ha,'/admin/app-release',{**release,'sha256':'bad'},400)
 post(a,ha,'/admin/app-release',release,200)
 post(a,ha,'/admin/app-release',release,409)
 assert get(b,'/app/version').json['release']['code']==6
 target=backup(p/'data/tunibiz.sqlite',p/'private-backup')
 with sqlite3.connect(target) as con:
  assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert con.execute('SELECT code FROM app_release').fetchone()[0]==6
 print('PASS version authorization, verified flag, URL, SHA256, increasing code and consistent SQLite snapshot')
