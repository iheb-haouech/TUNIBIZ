"""Administrator-controlled distribution metadata. No APK is marked available until explicitly verified."""
import hashlib,time,re,json
from flask import request,session,jsonify
def install(app,db,payload,err):
 with db() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS app_release(id INTEGER PRIMARY KEY CHECK(id=1),version TEXT NOT NULL,code INTEGER NOT NULL,url TEXT NOT NULL,sha256 TEXT NOT NULL,notes TEXT NOT NULL,created INTEGER NOT NULL)""")
 def admin(c):
  t=session.get('admin_token')
  return isinstance(t,str) and c.execute('SELECT 1 FROM admin_sessions WHERE digest=? AND expires>?',(hashlib.sha256(t.encode()).hexdigest(),int(time.time()))).fetchone()
 def latest(c):
  r=c.execute('SELECT version,code,url,sha256,notes,created FROM app_release WHERE id=1').fetchone()
  return dict(r) if r else None
 @app.get('/api/app/version')
 def app_version():
  with db() as c:return jsonify(release=latest(c))
 @app.post('/api/admin/app-release')
 def publish_app_release():
  p=payload();v=p.get('version');code=p.get('code');url=p.get('url');sha=p.get('sha256');notes=p.get('notes','')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not admin(c):return err('Administration requise',401)
   if not isinstance(v,str) or not re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}',v) or type(code)is not int or not 6<=code<=2100000000:return err('Version invalide')
   expected='https://github.com/iheb-haouech/TUNIBIZ/releases/download/v'+v+'/TUNIBIZ-v'+v+'.apk'
   if url!=expected or not isinstance(sha,str) or not re.fullmatch(r'[a-fA-F0-9]{64}',sha) or not isinstance(notes,str) or len(notes)>1500:return err('URL officielle, empreinte SHA-256 et notes requises')
   if p.get('verified') is not True:return err('Vérifiez le fichier et sa signature avant publication')
   old=latest(c)
   if old and code<=old['code']:return err('Le code de version doit augmenter',409)
   c.execute('INSERT INTO app_release VALUES(1,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,code=excluded.code,url=excluded.url,sha256=excluded.sha256,notes=excluded.notes,created=excluded.created',(v,code,url,sha.lower(),notes,int(time.time())))
   c.execute("INSERT INTO admin_operations(action,details) VALUES('app_release',?)",(json.dumps({'version':v,'code':code},sort_keys=True),))
  return jsonify(ok=True)
