"""Google OAuth / OpenID Connect, configured by deployment owner. No Gmail scopes."""
import os,secrets,time,hashlib,base64
from urllib.parse import urlencode,urlsplit
from flask import session,request,redirect,jsonify
from werkzeug.security import generate_password_hash
def config():
 cid=os.getenv('TUNIBIZ_GOOGLE_CLIENT_ID','');secret=os.getenv('TUNIBIZ_GOOGLE_CLIENT_SECRET','');uri=os.getenv('TUNIBIZ_GOOGLE_REDIRECT_URI','')
 return cid,secret,uri
def verify(token,cid):
 from google.oauth2.id_token import verify_oauth2_token
 from google.auth.transport.requests import Request
 claims=verify_oauth2_token(token,Request(),cid)
 if claims.get('email_verified') is not True or not claims.get('sub') or not claims.get('email'):raise ValueError('Identite Google non verifiee')
 return claims
def install(app,db,payload,err,throttle):
 with db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS google_accounts(subject TEXT PRIMARY KEY,account_id INTEGER UNIQUE NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE)')
 def enabled():
  cid,secret,uri=config()
  return bool(cid and secret and urlsplit(uri).scheme=='https' and urlsplit(uri).path=='/auth/google/callback')
 def establish(claims):
  sub=claims['sub'];email=claims['email'].lower();name=str(claims.get('name') or email)[:80]
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   row=c.execute('SELECT account_id FROM google_accounts WHERE subject=?',(sub,)).fetchone()
   if row:aid=row['account_id']
   else:
    if c.execute('SELECT 1 FROM consumer_accounts WHERE email=?',(email,)).fetchone():raise ValueError('Compte email existant : utilisez votre connexion habituelle. Aucun rattachement automatique.')
    aid=c.execute('INSERT INTO consumer_accounts(name,email,password) VALUES(?,?,?)',(name,email,generate_password_hash(secrets.token_urlsafe(48)))).lastrowid
    c.execute('INSERT INTO google_accounts VALUES(?,?)',(sub,aid))
   old=session.get('wallet_token')
   if isinstance(old,str):c.execute('DELETE FROM wallet_sessions WHERE digest=?',(hashlib.sha256(old.encode()).hexdigest(),))
   token=secrets.token_urlsafe(32)
   c.execute('INSERT INTO wallet_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),aid,int(time.time())+30*86400))
  for k in ('card','card_hash','wallet_card'):session.pop(k,None)
  session['wallet_token']=token;session.permanent=True
  session['google_reauth']=int(time.time())
 @app.get('/api/google/config')
 def google_config():return jsonify(enabled=enabled(),client_id=config()[0] if enabled() else '')
 @app.get('/auth/google/start')
 def google_start():
  if not enabled():return err('Connexion Google non configuree',503)
  cid,secret,uri=config()
  state=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
  session['google_flow']={'state':state,'nonce':nonce,'verifier':verifier,'expires':int(time.time())+600}
  challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
  return redirect('https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':cid,'redirect_uri':uri,'response_type':'code','scope':'openid email profile','state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256','prompt':'select_account'}))
 @app.get('/auth/google/callback')
 def google_callback():
  flow=session.pop('google_flow',None)
  if not enabled() or not flow or flow['expires']<time.time() or not secrets.compare_digest(flow['state'],request.args.get('state','')) or not request.args.get('code'):return err('Connexion Google annulee ou invalide',400)
  import requests
  cid,secret,uri=config()
  try:
   r=requests.post('https://oauth2.googleapis.com/token',data={'code':request.args['code'],'client_id':cid,'client_secret':secret,'redirect_uri':uri,'grant_type':'authorization_code','code_verifier':flow['verifier']},timeout=10);r.raise_for_status()
   claims=verify(r.json()['id_token'],cid)
   if claims.get('nonce')!=flow['nonce']:raise ValueError('Nonce invalide')
   establish(claims)
  except Exception:return err('Connexion Google impossible. Si un compte email existe, utilisez votre mot de passe.',401)
  return redirect('/wallet')
 @app.post('/api/google/login')
 def google_mobile():
  if not enabled():return err('Connexion Google non configuree',503)
  if not throttle('google_login',request.remote_addr or 'local',20):return err('Trop de tentatives',429)
  token=payload().get('id_token')
  if not isinstance(token,str) or not 1<=len(token)<=10000:return err('Jeton invalide')
  try:establish(verify(token,config()[0]))
  except Exception:return err('Identite Google invalide ou compte email existant',401)
  return jsonify(ok=True)
