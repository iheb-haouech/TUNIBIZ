"""Consumer email ownership confirmation and bounded welcome-abuse memory."""
import hashlib,hmac,os,re,secrets,time
from flask import request,session,jsonify,send_from_directory
import password_recovery

def required(production=False):
 return os.getenv('TUNIBIZ_REQUIRE_EMAIL_VERIFICATION','1' if production else '0')=='1'

def welcome_identity(email,secret):
 return hmac.new(secret.encode(),('welcome:'+email.strip().lower()).encode(),hashlib.sha256).hexdigest()

def send_confirmation(email,token):
 import requests
 r=requests.post('https://api.brevo.com/v3/smtp/email',headers={'api-key':os.environ['TUNIBIZ_BREVO_KEY']},
  json={'sender':{'name':'TUNIBIZ','email':os.environ['TUNIBIZ_EMAIL_FROM']},'to':[{'email':email}],
   'subject':'Confirmez votre adresse email TUNIBIZ',
   'textContent':'Confirmez votre adresse (lien à usage unique valable 20 minutes) : '+password_recovery.ORIGIN+'/verify-email#'+token},timeout=8)
 r.raise_for_status()

def install(app,db,payload,err,throttle,production):
 with db() as c:
  if 'email_verified' not in {r['name'] for r in c.execute('PRAGMA table_info(consumer_accounts)')}:
   c.execute('ALTER TABLE consumer_accounts ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0')
  c.executescript("""
  CREATE TABLE IF NOT EXISTS email_confirmations(digest TEXT PRIMARY KEY,account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,expires INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS welcome_claims(identity_digest TEXT NOT NULL,shop_id INTEGER NOT NULL REFERENCES shops(id),expires INTEGER NOT NULL,PRIMARY KEY(identity_digest,shop_id));
  """)
  # Preserve existing memberships without ever retaining plaintext email in the claims table.
  c.execute('UPDATE consumer_accounts SET email_verified=1 WHERE id IN (SELECT account_id FROM google_accounts)')
  for r in c.execute('SELECT a.email,m.shop_id FROM store_memberships m JOIN consumer_accounts a ON a.id=m.account_id'):
   c.execute('INSERT OR IGNORE INTO welcome_claims VALUES(?,?,?)',(welcome_identity(r['email'],app.secret_key),r['shop_id'],int(time.time())+90*86400))
 def account(c):
  t=session.get('wallet_token')
  return c.execute('SELECT a.id,a.email,a.email_verified FROM consumer_accounts a JOIN wallet_sessions s ON s.account_id=a.id WHERE s.digest=? AND s.expires>?',(hashlib.sha256(t.encode()).hexdigest(),int(time.time()))).fetchone() if isinstance(t,str) else None
 @app.get('/verify-email')
 def verification_page():return send_from_directory(app.static_folder,'verify-email.html')
 @app.get('/api/verification/status')
 def verification_status():
  with db() as c:
   a=account(c)
   if not a:return err('Connexion au portefeuille requise',401)
   google=c.execute('SELECT 1 FROM google_accounts WHERE account_id=?',(a['id'],)).fetchone()
   return jsonify(verified=bool(a['email_verified'] or google),required=required(production),delivery_enabled=password_recovery.ready())
 @app.post('/api/verification/request')
 def verification_request():
  with db() as c:a=account(c)
  if not a:return err('Connexion au portefeuille requise',401)
  if a['email_verified']:return jsonify(message='Adresse déjà confirmée.')
  if not password_recovery.ready():return err('Confirmation email indisponible. Contactez TUNIBIZ.',503)
  if not throttle('verify_ip',request.remote_addr or 'local',10) or not throttle('verify_account',str(a['id']),3):return err('Réessayez plus tard.',429)
  token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
  with db() as c:
   c.execute('DELETE FROM email_confirmations WHERE account_id=? OR expires<=?',(a['id'],int(time.time())))
   c.execute('INSERT INTO email_confirmations VALUES(?,?,?)',(digest,a['id'],int(time.time())+1200))
  try:send_confirmation(a['email'],token)
  except Exception:
   with db() as c:c.execute('DELETE FROM email_confirmations WHERE digest=?',(digest,))
   app.logger.warning('Email confirmation delivery unavailable')
   return err('Envoi temporairement indisponible. Réessayez.',503)
  return jsonify(message='Lien envoyé. Consultez votre boîte mail.')
 @app.post('/api/verification/confirm')
 def verification_confirm():
  token=payload().get('token')
  if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):return err('Lien invalide')
  if not throttle('verify_confirm',request.remote_addr or 'local',20):return err('Réessayez plus tard.',429)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   a=c.execute('SELECT account_id FROM email_confirmations WHERE digest=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
   if not a:return err('Lien expiré ou déjà utilisé')
   c.execute('UPDATE consumer_accounts SET email_verified=1 WHERE id=?',(a['account_id'],))
   c.execute('DELETE FROM email_confirmations WHERE account_id=?',(a['account_id'],))
  return jsonify(message='Adresse confirmée. Retournez dans votre portefeuille.')
 @app.before_request
 def require_email_for_scan():
  if request.method=='POST' and request.path=='/api/wallet/store-scan' and required(production):
   with db() as c:
    a=account(c)
    if a and not a['email_verified'] and not c.execute('SELECT 1 FROM google_accounts WHERE account_id=?',(a['id'],)).fetchone():
     return err('Vérifiez votre email avant de rejoindre un commerce.',403)
