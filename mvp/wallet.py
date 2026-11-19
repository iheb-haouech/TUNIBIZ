"""Consumer wallet. Merchant-issued cards retain separate point balances."""
import hashlib,re,secrets,time
from flask import jsonify,session,request,send_from_directory
from werkzeug.security import generate_password_hash,check_password_hash

def install(app,db,payload,clean,err):
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS consumer_accounts(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS wallet_cards(customer_id INTEGER PRIMARY KEY REFERENCES crm_customers(id) ON DELETE CASCADE,account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,card_hash TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS wallet_sessions(digest TEXT PRIMARY KEY,account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,expires INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS wallet_attempts(kind TEXT NOT NULL,subject TEXT NOT NULL,window INTEGER NOT NULL,count INTEGER NOT NULL,PRIMARY KEY(kind,subject));
  """)
 def digest(t):return hashlib.sha256(t.encode()).hexdigest()
 def clear_card():
  for k in ('card','card_hash','wallet_card'):session.pop(k,None)
 def account(c):
  token=session.get('wallet_token')
  if not isinstance(token,str):return None
  return c.execute('SELECT a.id,a.name,a.email FROM wallet_sessions s JOIN consumer_accounts a ON a.id=s.account_id WHERE s.digest=? AND s.expires>?',(digest(token),int(time.time()))).fetchone()
 def limit(kind,subject,n=12):
  now=int(time.time());window=now//900
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   c.execute('DELETE FROM wallet_attempts WHERE window<?',(window-1,))
   row=c.execute('SELECT window,count FROM wallet_attempts WHERE kind=? AND subject=?',(kind,subject)).fetchone()
   count=row['count'] if row and row['window']==window else 0
   if count>=n:return False
   c.execute('INSERT INTO wallet_attempts(kind,subject,window,count) VALUES(?,?,?,1) ON CONFLICT(kind,subject) DO UPDATE SET count=CASE WHEN window=excluded.window THEN count+1 ELSE 1 END,window=excluded.window',(kind,subject,window))
   return True
 def establish(c,aid):
  old=session.get('wallet_token')
  if isinstance(old,str):c.execute('DELETE FROM wallet_sessions WHERE digest=?',(digest(old),))
  token=secrets.token_urlsafe(32);now=int(time.time())
  c.execute('DELETE FROM wallet_sessions WHERE expires<=?',(now,))
  c.execute('INSERT INTO wallet_sessions VALUES(?,?,?)',(digest(token),aid,now+7*86400))
  clear_card();session.pop('google_reauth',None);session['wallet_token']=token
 @app.before_request
 def guard_wallet_selection():
  if not session.get('wallet_card'):return
  with db() as c:
   a=account(c)
   if not a or not c.execute("""SELECT 1 FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash
     WHERE w.account_id=? AND w.customer_id=? AND w.card_hash=?""",(a['id'],session.get('card'),session.get('card_hash'))).fetchone():clear_card()
 @app.get('/wallet')
 def wallet_page():return send_from_directory(app.static_folder,'wallet.html')
 @app.post('/api/wallet/register')
 def register():
  p=payload();name=clean(p.get('name'),80);email=clean(p.get('email'),180).lower();pw=p.get('password')
  if not name or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or not isinstance(pw,str) or not 12<=len(pw)<=128:return err('Nom, email valide et mot de passe de 12 a 128 caracteres requis')
  if not limit('register',request.remote_addr or 'local',10):return err('Trop de demandes. Reessayez plus tard.',429)
  hashed=generate_password_hash(pw)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if c.execute('SELECT 1 FROM consumer_accounts WHERE email=?',(email,)).fetchone():return err('Impossible de creer ce compte',409)
   aid=c.execute('INSERT INTO consumer_accounts(name,email,password) VALUES(?,?,?)',(name,email,hashed)).lastrowid
   establish(c,aid)
  return jsonify(ok=True),201
 @app.post('/api/wallet/login')
 def wallet_login():
  p=payload();email=clean(p.get('email'),180).lower();pw=p.get('password')
  if not isinstance(pw,str) or not 1<=len(pw)<=128:return err('Identifiants incorrects',401)
  if not limit('login',request.remote_addr or 'local',20):return err('Trop de tentatives. Reessayez plus tard.',429)
  with db() as c:
   a=c.execute('SELECT id,password FROM consumer_accounts WHERE email=?',(email,)).fetchone()
   if not a or not check_password_hash(a['password'],pw):return err('Identifiants incorrects',401)
   establish(c,a['id'])
  return jsonify(ok=True)
 @app.post('/api/wallet/logout')
 def wallet_logout():
  with db() as c:
   t=session.pop('wallet_token',None)
   if isinstance(t,str):c.execute('DELETE FROM wallet_sessions WHERE digest=?',(digest(t),))
  session.pop('google_reauth',None);clear_card()
  return jsonify(ok=True)
 @app.get('/api/wallet')
 def wallet_view():
  with db() as c:
   a=account(c)
   if not a:return err('Connectez votre portefeuille',401)
   cards=[dict(r) for r in c.execute("""WITH balances AS (
     SELECT customer_id,SUM(points) points,COUNT(CASE WHEN kind='purchase' THEN 1 END) purchases
     FROM loyalty_ledger GROUP BY customer_id)
     SELECT w.customer_id id,s.name shop,s.city,a.name card_name,a.consent,
     COALESCE(b.points,0) points,COALESCE(b.purchases,0) purchases,
     (SELECT COUNT(*) FROM rewards r WHERE r.shop_id=a.shop_id AND r.active=1 AND r.cost<=COALESCE(b.points,0) AND EXISTS (SELECT 1 FROM subscriptions t WHERE t.shop_id=a.shop_id AND t.status='active' AND t.paid_until>date('now','+1 hour'))) eligible
     FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash JOIN shops s ON s.id=a.shop_id
     LEFT JOIN balances b ON b.customer_id=a.id WHERE w.account_id=? ORDER BY s.name,a.id""",(a['id'],))]
   google_linked=c.execute('SELECT 1 FROM google_accounts WHERE account_id=?',(a['id'],)).fetchone()
  return jsonify(profile={**dict(a),'google_linked':bool(google_linked)},cards=cards)
 @app.post('/api/wallet/link')
 def link():
  code=payload().get('code')
  if not isinstance(code,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32}',code):return err('Code de carte incorrect',400)
  with db() as c:
   a=account(c)
   if not a:return err('Connexion requise',401)
   aid=a['id']
  if not limit('link',str(aid),20):return err('Trop de tentatives',429)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   a=account(c)
   if not a:return err('Connexion requise',401)
   card=c.execute('SELECT id,code_hash FROM crm_customers WHERE code_hash=?',(digest(code),)).fetchone()
   if not card:return err('Code de carte incorrect',404)
   old=c.execute('SELECT account_id,card_hash FROM wallet_cards WHERE customer_id=?',(card['id'],)).fetchone()
   if old and old['card_hash']==card['code_hash'] and old['account_id']!=a['id']:return err('Carte deja rattachee a un autre portefeuille',409)
   c.execute('INSERT INTO wallet_cards VALUES(?,?,?) ON CONFLICT(customer_id) DO UPDATE SET account_id=excluded.account_id,card_hash=excluded.card_hash',(card['id'],a['id'],card['code_hash']))
  return jsonify(ok=True,id=card['id'])
 @app.post('/api/wallet/select')
 def select():
  cid=payload().get('id')
  if type(cid)is not int:return err('Carte invalide')
  with db() as c:
   a=account(c)
   if not a:return err('Connexion requise',401)
   card=c.execute("""SELECT a.id,a.code_hash FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash
     WHERE w.account_id=? AND w.customer_id=?""",(a['id'],cid)).fetchone()
   if not card:return err('Carte indisponible',404)
  session['card']=card['id'];session['card_hash']=card['code_hash'];session['wallet_card']=True
  return jsonify(ok=True)
 @app.post('/api/wallet/unlink')
 def unlink():
  cid=payload().get('id')
  if type(cid)is not int:return err('Carte invalide')
  with db() as c:
   a=account(c)
   if not a:return err('Connexion requise',401)
   r=c.execute('DELETE FROM wallet_cards WHERE account_id=? AND customer_id=?',(a['id'],cid))
   if not r.rowcount:return err('Carte indisponible',404)
   c.execute('DELETE FROM loyalty_scan_tokens WHERE customer_id=?',(cid,))
  if session.get('card')==cid:clear_card()
  return jsonify(ok=True)

 @app.post('/api/wallet/delete')
 def delete_account():
  pw=payload().get('password')
  if not isinstance(pw,str) or len(pw)>128:return err('Confirmation requise')
  with db() as c:
   a=account(c)
   if not a:return err('Connexion requise',401)
   aid=a['id']
  if not limit('delete',str(aid),5):return err('Trop de tentatives',429)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   a=account(c)
   if not a:return err('Connexion requise',401)
   row=c.execute('SELECT password FROM consumer_accounts WHERE id=?',(a['id'],)).fetchone()
   google_ok=bool(c.execute('SELECT 1 FROM google_accounts WHERE account_id=?',(a['id'],)).fetchone()) and int(session.get('google_reauth',0))>time.time()-300 and payload().get('confirm_google') is True
   if not row or not (google_ok or (pw and check_password_hash(row['password'],pw))):return err('Reconnectez-vous avec Google' if payload().get('confirm_google') is True else 'Mot de passe incorrect',401)
   ids=[r['customer_id'] for r in c.execute('SELECT w.customer_id FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash WHERE w.account_id=? UNION SELECT m.customer_id FROM store_memberships m JOIN crm_customers x ON x.id=m.customer_id AND x.code_hash=m.card_hash WHERE m.account_id=? AND NOT EXISTS (SELECT 1 FROM wallet_cards w WHERE w.customer_id=m.customer_id AND w.account_id<>m.account_id)',(a['id'],a['id']))]
   for cid in ids:
    c.execute("UPDATE crm_customers SET name='Client anonymise',phone='',consent=0,code_hash=? WHERE id=?",(digest(secrets.token_urlsafe(32)),cid))
    c.execute("UPDATE loyalty_ledger SET label=CASE WHEN kind='purchase' THEN 'Achat' ELSE 'Recompense' END WHERE customer_id=?",(cid,))
    c.execute('DELETE FROM loyalty_scan_tokens WHERE customer_id=?',(cid,))
   c.execute('DELETE FROM wallet_attempts WHERE subject=? AND kind IN (\'link\',\'delete\')',(str(a['id']),))
   c.execute('DELETE FROM consumer_accounts WHERE id=?',(a['id'],))
  session.pop('wallet_token',None);session.pop('google_reauth',None);clear_card()
  return jsonify(ok=True)
