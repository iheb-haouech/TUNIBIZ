import os,subprocess,sys,tempfile
from pathlib import Path
p=Path(__file__).parent
env={**os.environ,'TUNIBIZ_ENV':'production'}
env.pop('TUNIBIZ_SECRET',None);env.pop('TUNIBIZ_DATA_DIR',None)
r=subprocess.run([sys.executable,'-c','import app'],cwd=p,env=env,capture_output=True,text=True)
assert r.returncode!=0 and 'Production requires' in r.stderr
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 env.update(TUNIBIZ_SECRET='test-only-'+'x'*64,TUNIBIZ_DATA_DIR=tmp)
 r=subprocess.run([sys.executable,'-c',"""from app import app,db
assert app.config['SESSION_COOKIE_SECURE']
with db() as c:assert c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0
client=app.test_client()
r=client.get('/api/session',base_url='https://localhost')
assert 'Secure' in r.headers['Set-Cookie'] and 'HttpOnly' in r.headers['Set-Cookie']
assert r.headers['Strict-Transport-Security']=='max-age=31536000'
assert client.get('/privacy').status_code==200
assert client.get('/account-deletion').status_code==200
print('PASS production: no demo provisioning, Secure/HttpOnly cookie, HSTS, privacy routes')
"""],cwd=p,env=env,capture_output=True,text=True);assert r.returncode==0,r.stderr;print(r.stdout)
print('PASS missing production credentials refused')
