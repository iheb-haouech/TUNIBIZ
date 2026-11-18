"""Isolated pilot homepage, download and password recovery tests."""
import os,sys,tempfile,shutil
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 sys.path.insert(0,str(p))
 from app import app,db
 import password_recovery as recovery
 def client():
  c=app.test_client();return c,{'X-CSRF-Token':c.get('/api/session').json['csrf']}
 def post(pair,path,body,status=200):
  c,h=pair;r=c.post('/api'+path,json=body,headers=h);assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True));return r.json
 a=client();b=client();pw='QA-old-passphrase';new='QA-new-passphrase'
 assert a[0].get('/').status_code==200 and b'home-premium.js' in a[0].get('/').data
 for path in ['/solutions','/download','/forgot-password','/reset-password']:assert a[0].get(path).status_code==200
 post(a,'/wallet/register',{'name':'QA','email':'qa@example.test','password':pw},201)
 post(b,'/wallet/login',{'email':'qa@example.test','password':pw})
 with patch.object(recovery,'ready',return_value=False):post(a,'/password/request',{'email':'qa@example.test','kind':'consumer'},503)
 sent=[]
 with patch.object(recovery,'ready',return_value=True),patch.object(recovery,'send_link',side_effect=lambda email,token:sent.append((email,token))):
  one=post(a,'/password/request',{'email':'qa@example.test','kind':'consumer'})
  two=post(a,'/password/request',{'email':'missing@example.test','kind':'consumer'})
  assert one==two and len(sent)==1
 token=sent[0][1]
 with db() as c:
  assert c.execute('SELECT digest FROM password_resets').fetchone()[0]!=token
 post(a,'/password/reset',{'token':token,'password':new})
 post(a,'/password/reset',{'token':token,'password':new},400)
 assert b[0].get('/api/wallet').status_code==401
 post(b,'/wallet/login',{'email':'qa@example.test','password':pw},401)
 post(b,'/wallet/login',{'email':'qa@example.test','password':new})
 print('PASS recovery: disabled config, enumeration protection, hashed single use token, session revocation and new password')
 print('PASS public homepage, solutions, download and recovery routes')
