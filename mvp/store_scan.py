"""Store QR membership and purchase approvals. All awards are server-side."""
import base64,hashlib,io,re,secrets,time
from flask import jsonify,session,send_from_directory,send_file,request
import qrcode
from verification import welcome_identity

BASE='https://ihebhaouech.pythonanywhere.com'
def digest(v):return hashlib.sha256(v.encode()).hexdigest()
def image(url):
 b=io.BytesIO();qrcode.make(url).save(b,format='PNG');b.seek(0)
 return send_file(b,mimetype='image/png',max_age=0)
def install(app,db,payload,merchant,err):
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS store_memberships(
    account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,
    shop_id INTEGER NOT NULL REFERENCES shops(id),
    customer_id INTEGER NOT NULL UNIQUE REFERENCES crm_customers(id),
    card_hash TEXT NOT NULL, PRIMARY KEY(account_id,shop_id));
  CREATE TABLE IF NOT EXISTS store_scan_requests(
    id TEXT PRIMARY KEY,account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,
    shop_id INTEGER NOT NULL REFERENCES shops(id),customer_id INTEGER NOT NULL REFERENCES crm_customers(id),
    created INTEGER NOT NULL,expires INTEGER NOT NULL,state TEXT NOT NULL DEFAULT 'pending',
    points INTEGER NOT NULL DEFAULT 0,decided INTEGER);
  CREATE INDEX IF NOT EXISTS scan_queue ON store_scan_requests(shop_id,state,expires);
  CREATE UNIQUE INDEX IF NOT EXISTS scan_one_pending ON store_scan_requests(account_id,shop_id) WHERE state='pending';
  """)
 def account(c):
  t=session.get('wallet_token')
  if not isinstance(t,str):return None
  return c.execute('SELECT a.id,a.name,a.email FROM consumer_accounts a JOIN wallet_sessions w ON w.account_id=a.id WHERE w.digest=? AND w.expires>?',(digest(t),int(time.time()))).fetchone()
 def shop(c,slug):
  return c.execute("SELECT s.id,s.slug,s.name,s.city FROM shops s JOIN subscriptions t ON t.shop_id=s.id WHERE s.slug=? AND t.status='active' AND t.paid_until>date('now','+1 hour')",(slug,)).fetchone()
 def expire(c):
  c.execute("UPDATE store_scan_requests SET state='expired' WHERE state='pending' AND expires<=?",(int(time.time()),))
 def active(c,sid):
  return c.execute("SELECT 1 FROM subscriptions WHERE shop_id=? AND status='active' AND paid_until>date('now','+1 hour')",(sid,)).fetchone()
 def merchant_session(c,sid):
  t=session.get('merchant_token')
  return isinstance(t,str) and c.execute("SELECT 1 FROM merchant_sessions m JOIN users u ON u.id=m.user_id WHERE m.digest=? AND m.expires>? AND u.shop_id=?",(digest(t),int(time.time()),sid)).fetchone()
 @app.get('/qr/download.png')
 def store_download_qr():return image(BASE+'/download')
 @app.get('/join/<slug>')
 def store_join_page(slug):
  with db() as c:
   if not shop(c,slug):return err('Commerce indisponible',404)
  return send_from_directory(app.static_folder,'store-join.html')
 @app.get('/api/store/<slug>')
 def store_info(slug):
  with db() as c:
   row=shop(c,slug)
   if not row:return err('Commerce indisponible',404)
   return jsonify(shop=dict(row))
 @app.post('/api/wallet/store-scan')
 def store_scan():
  p=payload();slug=p.get('slug')
  if not isinstance(slug,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',slug):return err('QR commerce invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');a=account(c);s=shop(c,slug)
   if not a:return err('Connexion au portefeuille requise',401)
   if not s:return err('Commerce indisponible',404)
   aid,sid=a['id'],s['id'];now=int(time.time());expire(c)
   m=c.execute("SELECT m.customer_id,m.card_hash,a.code_hash FROM store_memberships m JOIN crm_customers a ON a.id=m.customer_id WHERE m.account_id=? AND m.shop_id=?",(aid,sid)).fetchone()
   welcome=0
   if m:
    cid=m['customer_id'];h=m['card_hash']
    if h!=m['code_hash']:return err('Carte revoquee. Contactez le commerce.',409)
    owner=c.execute('SELECT account_id FROM wallet_cards WHERE customer_id=?',(cid,)).fetchone()
    if owner and owner['account_id']!=aid:return err('Carte deja rattachee',409)
   else:
    linked=c.execute("SELECT a.id,a.code_hash FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash WHERE w.account_id=? AND a.shop_id=? ORDER BY a.id LIMIT 1",(aid,sid)).fetchone()
    if linked:cid,h=linked['id'],linked['code_hash']
    else:
     h=digest(secrets.token_urlsafe(24))
     cid=c.execute('INSERT INTO crm_customers(shop_id,name,consent,code_hash) VALUES(?,?,0,?)',(sid,a['name'],h)).lastrowid
     welcome=3
    c.execute('INSERT INTO store_memberships VALUES(?,?,?,?)',(aid,sid,cid,h))
   c.execute('INSERT OR IGNORE INTO wallet_cards VALUES(?,?,?)',(cid,aid,h))
   if welcome:
    identity=welcome_identity(a['email'],app.secret_key)
    c.execute('DELETE FROM welcome_claims WHERE expires<=?',(now,))
    claimed=c.execute('SELECT 1 FROM welcome_claims WHERE identity_digest=? AND shop_id=?',(identity,sid)).fetchone()
    if claimed:return jsonify(status='welcome',points=0,shop=s['name'],customer_id=cid,welcome_previously_claimed=True),201
    c.execute('INSERT INTO welcome_claims VALUES(?,?,?)',(identity,sid,now+90*86400))
    c.execute("INSERT INTO loyalty_ledger(customer_id,kind,points,label,request_key) VALUES(?,'welcome',3,'Bienvenue','welcome:'||?)",(cid,str(cid)))
    return jsonify(status='welcome',points=3,shop=s['name'],customer_id=cid),201
   pending=c.execute("SELECT id,expires FROM store_scan_requests WHERE account_id=? AND shop_id=? AND state='pending'",(aid,sid)).fetchone()
   if pending:return jsonify(status='pending',id=pending['id'],expires=pending['expires'],shop=s['name'],duplicate=True)
   # Avoid rapid rescan immediately after a completed request.
   if c.execute("SELECT 1 FROM store_scan_requests WHERE account_id=? AND shop_id=? AND decided>? LIMIT 1",(aid,sid,now-30)).fetchone():return err('Attendez 30 secondes avant une nouvelle demande',429)
   rid=secrets.token_urlsafe(18)
   c.execute("INSERT INTO store_scan_requests(id,account_id,shop_id,customer_id,created,expires) VALUES(?,?,?,?,?,?)",(rid,aid,sid,cid,now,now+300))
   return jsonify(status='pending',id=rid,expires=now+300,shop=s['name']),201
 @app.get('/api/wallet/store-scans')
 def store_scan_history():
  with db() as c:
   a=account(c)
   if not a:return err('Connexion requise',401)
   expire(c)
   return jsonify(requests=[dict(r) for r in c.execute("SELECT r.id,s.name shop,r.state,r.points,r.created,r.expires FROM store_scan_requests r JOIN shops s ON s.id=r.shop_id WHERE r.account_id=? ORDER BY r.created DESC LIMIT 30",(a['id'],))])
 @app.get('/api/crm/store-qr')
 def store_qr():
  sid=merchant()
  with db() as c:
   r=c.execute('SELECT slug,name FROM shops WHERE id=?',(sid,)).fetchone()
  url=BASE+'/join/'+r['slug'];b=io.BytesIO();qrcode.make(url).save(b,format='PNG')
  return jsonify(shop=r['name'],url=url,download_url=BASE+'/download',png=base64.b64encode(b.getvalue()).decode())
 @app.get('/api/crm/store-scans')
 def store_queue():
  sid=merchant()
  with db() as c:
   expire(c)
   return jsonify(requests=[dict(r) for r in c.execute("SELECT r.id,a.name,r.created,r.expires,1 default_points FROM store_scan_requests r JOIN crm_customers a ON a.id=r.customer_id WHERE r.shop_id=? AND r.state='pending' ORDER BY r.created LIMIT 100",(sid,))])
 @app.post('/api/crm/store-scan/decide')
 def store_decide():
  sid=merchant();p=payload();rid=p.get('id');action=p.get('action');pts=p.get('points',1)
  if not isinstance(rid,str) or action not in ('approve','reject') or type(pts)is not int or not 1<=pts<=1000:return err('Action ou nombre de points invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not active(c,sid) or not merchant_session(c,sid):return err('Commerce indisponible',403)
   expire(c);r=c.execute('SELECT * FROM store_scan_requests WHERE id=? AND shop_id=?',(rid,sid)).fetchone()
   if not r:return err('Demande introuvable',404)
   if r['state']!='pending':
    if (r['state']=='approved' and action=='approve' and r['points']==pts) or (r['state']=='rejected' and action=='reject'):return jsonify(ok=True,duplicate=True,points=r['points'])
    return err('Demande deja traitee ou expiree',409)
   if not c.execute("SELECT 1 FROM store_memberships m JOIN crm_customers a ON a.id=m.customer_id AND a.code_hash=m.card_hash JOIN wallet_cards w ON w.customer_id=a.id AND w.account_id=m.account_id AND w.card_hash=m.card_hash WHERE m.account_id=? AND m.shop_id=? AND m.customer_id=?",(r['account_id'],sid,r['customer_id'])).fetchone():return err('Carte indisponible',409)
   points=pts if action=='approve' else 0
   if points:c.execute("INSERT INTO loyalty_ledger(customer_id,kind,amount,points,label,request_key) VALUES(?,'scan',0,?,'Achat valide - QR',?)",(r['customer_id'],points,'scan:'+rid))
   c.execute('UPDATE store_scan_requests SET state=?,points=?,decided=? WHERE id=?',('approved' if points else 'rejected',points,int(time.time()),rid))
  return jsonify(ok=True,points=points)
 @app.get('/merchant-qr')
 def store_merchant_page():return send_from_directory(app.static_folder,'store-merchant.html')
