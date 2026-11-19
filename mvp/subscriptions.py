"""Cash subscriptions, registration and independent administration."""
import math,secrets,time,hashlib,os,re
from datetime import date,timedelta
from flask import session,request,jsonify,send_from_directory
from werkzeug.security import generate_password_hash,check_password_hash
def install(app,db,payload,clean,err,throttle,production):
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS subscriptions(shop_id INTEGER PRIMARY KEY REFERENCES shops(id),status TEXT NOT NULL DEFAULT 'pending',paid_until TEXT NOT NULL DEFAULT '',radius INTEGER NOT NULL DEFAULT 1000,category TEXT NOT NULL DEFAULT 'general');
  CREATE TABLE IF NOT EXISTS cash_payments(id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),reference TEXT UNIQUE NOT NULL,amount INTEGER NOT NULL CHECK(amount=19000),created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS admin_sessions(digest TEXT PRIMARY KEY,expires INTEGER NOT NULL);
  """)
  c.execute("INSERT OR IGNORE INTO subscriptions(shop_id,status,paid_until) SELECT id,CASE WHEN slug='demo' AND ?=0 THEN 'active' ELSE 'pending' END,CASE WHEN slug='demo' AND ?=0 THEN '2099-12-31' ELSE '' END FROM shops",(int(production),int(production)))
  if 'category_detail' not in {r['name'] for r in c.execute('PRAGMA table_info(subscriptions)')}:c.execute("ALTER TABLE subscriptions ADD COLUMN category_detail TEXT NOT NULL DEFAULT ''")
  if 'archived_at' not in {r['name'] for r in c.execute('PRAGMA table_info(subscriptions)')}:c.execute('ALTER TABLE subscriptions ADD COLUMN archived_at TEXT')
  cols={r['name'] for r in c.execute('PRAGMA table_info(nearby_offers)')}
  if 'radius_override' not in cols:c.execute('ALTER TABLE nearby_offers ADD COLUMN radius_override INTEGER')
  if 'location_confirmed' not in {r['name'] for r in c.execute('PRAGMA table_info(nearby_locations)')}:c.execute('ALTER TABLE nearby_locations ADD COLUMN location_confirmed INTEGER NOT NULL DEFAULT 0')
 def digest(x):return hashlib.sha256(x.encode()).hexdigest()
 def admin(c):
  token=session.get('admin_token')
  return isinstance(token,str) and c.execute('SELECT 1 FROM admin_sessions WHERE digest=? AND expires>?',(digest(token),int(time.time()))).fetchone()
 @app.get('/admin')
 def admin_page():return send_from_directory(app.static_folder,'admin-cash.html')
 @app.get('/merchant-register')
 def register_page():return send_from_directory(app.static_folder,'merchant-register.html')
 @app.post('/api/merchant/register')
 def subscription_register():
  if not throttle('merchant_register',request.remote_addr or 'local',10):return err('Trop de demandes',429)
  p=payload();name=clean(p.get('name'));city=clean(p.get('city'));address=clean(p.get('address'),180);email=clean(p.get('email'),180).lower();pw=p.get('password');category=p.get('category');detail=clean(p.get('category_detail'),80)
  try:
   lat=float(p['lat']);lon=float(p['lon'])
   if not (math.isfinite(lat) and math.isfinite(lon) and 30<=lat<=38 and 7<=lon<=12 and p.get('confirmed') is True):raise ValueError()
  except (ValueError,TypeError,KeyError):return err('Confirmez le point exact du commerce sur la carte')
  if not name or not city or not address or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or not isinstance(pw,str) or not 12<=len(pw)<=128 or category not in ('grocery_general', 'drugstore', 'grocery', 'coffee', 'restaurant', 'bakery', 'shopping', 'clothing', 'other', 'general', 'drinks', 'beauty'):return err('Informations invalides')
  if category=='other' and not detail:return err('Précisez le type d’établissement')
  if category!='other':detail=''
  hashed=generate_password_hash(pw)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():return err('Inscription indisponible',409)
   sid=c.execute('INSERT INTO shops(slug,name,city) VALUES(?,?,?)',(secrets.token_hex(12),name,city)).lastrowid
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,email,hashed))
   c.execute('INSERT INTO nearby_locations(shop_id,lat,lon,address,location_confirmed) VALUES(?,?,?,?,1)',(sid,lat,lon,address))
   c.execute('INSERT INTO subscriptions(shop_id,category,category_detail) VALUES(?,?,?)',(sid,category,detail))
  return jsonify(status='pending',price_millimes=19000),201
 @app.post('/api/admin/login')
 def subscription_login():
  if not throttle('admin_login',request.remote_addr or 'local',10):return err('Trop de tentatives',429)
  hashed=os.environ.get('TUNIBIZ_ADMIN_PASSWORD_HASH','');pw=payload().get('password')
  if not hashed:return err('Administration non configuree',503)
  if not isinstance(pw,str) or len(pw)>128 or not check_password_hash(hashed,pw):return err('Identifiants incorrects',401)
  token=secrets.token_urlsafe(32)
  with db() as c:
   old=session.get('admin_token')
   if isinstance(old,str):c.execute('DELETE FROM admin_sessions WHERE digest=?',(digest(old),))
   c.execute('DELETE FROM admin_sessions WHERE expires<=?',(int(time.time()),))
   c.execute('INSERT INTO admin_sessions VALUES(?,?)',(digest(token),int(time.time())+14400))
  session['admin_token']=token
  return jsonify(ok=True)
 @app.post('/api/admin/logout')
 def subscription_logout():
  token=session.pop('admin_token',None)
  if isinstance(token,str):
   with db() as c:c.execute('DELETE FROM admin_sessions WHERE digest=?',(digest(token),))
  return jsonify(ok=True)
 @app.get('/api/admin/shops')
 def subscription_shops():
  with db() as c:
   if not admin(c):return err('Administration requise',401)
   shops=[dict(r) for r in c.execute('''SELECT s.id,s.name,s.city,t.status,t.paid_until,t.radius,t.category,t.category_detail,t.archived_at,l.lat,l.lon,l.address,l.location_confirmed FROM shops s JOIN subscriptions t ON s.id=t.shop_id LEFT JOIN nearby_locations l ON l.shop_id=s.id ORDER BY s.id DESC''')]
   offers=[dict(r) for r in c.execute('SELECT id,shop_id,title,active,radius_override FROM nearby_offers ORDER BY id DESC')]
  return jsonify(shops=shops,offers=offers)
 @app.post('/api/admin/shop')
 def subscription_change():
  p=payload();sid=p.get('id');action=p.get('action')
  if type(sid)is not int:return err('Commerce invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not admin(c):return err('Administration requise',401)
   t=c.execute('SELECT * FROM subscriptions WHERE shop_id=?',(sid,)).fetchone()
   if not t:return err('Commerce introuvable',404)
   if action=='archive':
    if p.get('confirm') is not True:return err('Confirmation obligatoire')
    if t['status']=='archived':return jsonify(ok=True,duplicate=True)
    c.execute("UPDATE subscriptions SET status='archived',archived_at=CURRENT_TIMESTAMP WHERE shop_id=?",(sid,))
    c.execute('DELETE FROM merchant_sessions WHERE user_id IN (SELECT id FROM users WHERE shop_id=?)',(sid,))
    c.execute("UPDATE store_scan_requests SET state='expired' WHERE shop_id=? AND state='pending'",(sid,))
   elif action=='restore':
    if p.get('confirm') is not True:return err('Confirmation obligatoire')
    if t['status']!='archived':return err('Commerce non archive',409)
    c.execute("UPDATE subscriptions SET status='blocked',archived_at=NULL WHERE shop_id=?",(sid,))
   elif t['status']=='archived':return err('Commerce archive : restaurez-le avant toute modification',409)
   elif action=='cash':
    ref=clean(p.get('reference'),80)
    if not ref:return err('Reference du recu obligatoire')
    old=c.execute('SELECT shop_id FROM cash_payments WHERE reference=?',(ref,)).fetchone()
    if old:return jsonify(ok=True,duplicate=True) if old['shop_id']==sid else err('Reference deja utilisee',409)
    loc=c.execute('SELECT location_confirmed FROM nearby_locations WHERE shop_id=?',(sid,)).fetchone()
    if not loc or not loc[0]:return err('Emplacement exact obligatoire')
    end=(max(date.today(),date.fromisoformat(t['paid_until']) if t['paid_until'] else date.today())+timedelta(days=30)).isoformat()
    c.execute('INSERT INTO cash_payments(shop_id,reference,amount) VALUES(?,?,19000)',(sid,ref))
    c.execute("UPDATE subscriptions SET paid_until=?,status='active' WHERE shop_id=?",(end,sid))
   elif action=='block':
    c.execute("UPDATE subscriptions SET status='blocked' WHERE shop_id=?",(sid,))
    c.execute('DELETE FROM merchant_sessions WHERE user_id IN (SELECT id FROM users WHERE shop_id=?)',(sid,))
   elif action=='activate':
    if t['paid_until']<=date.today().isoformat() or not c.execute('SELECT 1 FROM nearby_locations WHERE shop_id=? AND location_confirmed=1',(sid,)).fetchone():return err('Paiement valide et emplacement requis')
    c.execute("UPDATE subscriptions SET status='active' WHERE shop_id=?",(sid,))
   elif action=='radius':
    r=p.get('radius')
    if type(r)is not int or not 100<=r<=10000:return err('Rayon entre 100 et 10000 metres')
    c.execute('UPDATE subscriptions SET radius=? WHERE shop_id=?',(r,sid))
   elif action=='offer_radius':
    r=p.get('radius');oid=p.get('offer_id')
    if type(oid)is not int or (r is not None and (type(r)is not int or not 100<=r<=10000)):return err('Rayon invalide')
    if not c.execute('UPDATE nearby_offers SET radius_override=? WHERE id=? AND shop_id=?',(r,oid,sid)).rowcount:return err('Offre introuvable',404)
   else:return err('Action invalide')
  return jsonify(ok=True)
