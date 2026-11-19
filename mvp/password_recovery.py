"""Password recovery via configured HTTPS transactional email provider."""
import os,re,secrets,hashlib,time
import gmail_delivery
from flask import request,jsonify,send_from_directory,session
from werkzeug.security import generate_password_hash
ORIGIN='https://ihebhaouech.pythonanywhere.com'
GENERIC='Si un compte correspondant existe, un lien de réinitialisation sera envoyé.'
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def ready():return gmail_delivery.ready()
def send_link(email,token):
 gmail_delivery.send(email,'Reinitialisation de votre mot de passe TUNIBIZ','Votre lien a usage unique (valable 20 minutes) : '+ORIGIN+'/reset-password#'+token+'\nSi vous n’avez rien demande, ignorez ce message.')

def install(app,db,payload,err,throttle):
 with db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS password_resets(digest TEXT PRIMARY KEY,kind TEXT NOT NULL,account_id INTEGER NOT NULL,expires INTEGER NOT NULL,password_version TEXT NOT NULL)')
 @app.get('/forgot-password')
 def forgot_page():return send_from_directory(app.static_folder,'recovery.html')
 @app.get('/reset-password')
 def reset_page():return send_from_directory(app.static_folder,'recovery.html')
 @app.get('/api/password/config')
 def password_config():return jsonify(enabled=ready())
 @app.post('/api/password/request')
 def password_request():
  p=payload();email=p.get('email');kind=p.get('kind')
  if kind not in ('consumer','merchant') or not isinstance(email,str) or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email.strip()) or len(email)>180:return err('Adresse email invalide')
  if not ready():return err('Envoi de récupération temporairement indisponible. Contactez TUNIBIZ.',503)
  email=email.strip().lower()
  if not throttle('recovery_ip',request.remote_addr or 'local',10) or not throttle('recovery_email',digest(kind+email),3):return err('Réessayez dans quelques minutes.',429)
  table='consumer_accounts' if kind=='consumer' else 'users'
  token=secrets.token_urlsafe(32);h=digest(token)
  with db() as c:
   a=c.execute(f'SELECT id,password FROM {table} WHERE email=?',(email,)).fetchone()
   if a and kind=='consumer' and c.execute('SELECT 1 FROM google_accounts WHERE account_id=?',(a['id'],)).fetchone():a=None
   c.execute('DELETE FROM password_resets WHERE expires<=?',(int(time.time()),))
   if a:
    c.execute('DELETE FROM password_resets WHERE kind=? AND account_id=?',(kind,a['id']))
    c.execute('INSERT INTO password_resets VALUES(?,?,?,?,?)',(h,kind,a['id'],int(time.time())+1200,digest(a['password'])))
  if a:
   try:send_link(email,token)
   except Exception:
    with db() as c:c.execute('DELETE FROM password_resets WHERE digest=?',(h,))
    app.logger.warning('Password recovery delivery failed')
  return jsonify(message=GENERIC)
 @app.post('/api/password/reset')
 def password_reset():
  p=payload();token=p.get('token');pw=p.get('password')
  if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token) or not isinstance(pw,str) or not 12<=len(pw)<=128:return err('Lien invalide ou mot de passe de 12 à 128 caractères requis')
  if not throttle('recovery_reset',request.remote_addr or 'local',20):return err('Réessayez dans quelques minutes.',429)
  h=digest(token)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   r=c.execute('SELECT * FROM password_resets WHERE digest=? AND expires>?',(h,int(time.time()))).fetchone()
   if not r:return err('Lien expiré ou déjà utilisé',400)
   kind=r['kind'];aid=r['account_id'];table='consumer_accounts' if kind=='consumer' else 'users'
   a=c.execute(f'SELECT password FROM {table} WHERE id=?',(aid,)).fetchone()
   if not a or not secrets.compare_digest(digest(a['password']),r['password_version']):return err('Lien expiré ou déjà utilisé')
   if kind=='consumer' and c.execute('SELECT 1 FROM google_accounts WHERE account_id=?',(aid,)).fetchone():return err('Utilisez votre connexion Google')
   c.execute(f'UPDATE {table} SET password=? WHERE id=?',(generate_password_hash(pw),aid))
   c.execute('DELETE FROM password_resets WHERE kind=? AND account_id=?',(kind,aid))
   if kind=='consumer':c.execute('DELETE FROM wallet_sessions WHERE account_id=?',(aid,))
   else:c.execute('DELETE FROM merchant_sessions WHERE user_id=?',(aid,))
  for k in ('wallet_token','merchant_token','card','card_hash','wallet_card','google_reauth'):session.pop(k,None)
  return jsonify(message='Mot de passe modifié. Connectez-vous à nouveau.')
