"""Cash subscriptions, registration and independent administration."""
import math,secrets,time,hashlib,os,re,json,io
from datetime import date,timedelta,datetime,timezone
from flask import session,request,jsonify,send_from_directory,send_file
from werkzeug.security import generate_password_hash,check_password_hash
CATEGORIES=('grocery_general','drugstore','grocery','coffee','restaurant','bakery','shopping','clothing','other')
def today():
 return datetime.now(timezone(timedelta(hours=1))).date()
def install(app,db,payload,clean,err,throttle,production):
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS subscriptions(shop_id INTEGER PRIMARY KEY REFERENCES shops(id),status TEXT NOT NULL DEFAULT 'pending',paid_until TEXT NOT NULL DEFAULT '',radius INTEGER NOT NULL DEFAULT 1000,category TEXT NOT NULL DEFAULT 'general');
  CREATE TABLE IF NOT EXISTS cash_payments(id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),reference TEXT UNIQUE NOT NULL,amount INTEGER NOT NULL CHECK(amount=19000),created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS admin_sessions(digest TEXT PRIMARY KEY,expires INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS admin_operations(id INTEGER PRIMARY KEY AUTOINCREMENT,shop_id INTEGER REFERENCES shops(id),action TEXT NOT NULL,details TEXT NOT NULL DEFAULT '{}',created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS storefront_hidden_photos(photo_id TEXT PRIMARY KEY REFERENCES storefront_photos(id) ON DELETE CASCADE,shop_id INTEGER NOT NULL REFERENCES shops(id));
  CREATE INDEX IF NOT EXISTS admin_operations_shop ON admin_operations(shop_id,id);
  CREATE INDEX IF NOT EXISTS cash_payments_created ON cash_payments(created);

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
 def journal(c,action,sid=None,details=None):
  c.execute('INSERT INTO admin_operations(shop_id,action,details) VALUES(?,?,?)',(sid,action,json.dumps(details or {},ensure_ascii=False,sort_keys=True)))
 @app.get('/api/admin/history')
 def subscription_history():
  with db() as c:
   if not admin(c):return err('Administration requise',401)
   offset=request.args.get('offset',0,type=int)
   if not 0<=offset<=1000000:return err('Page invalide')
   payments=[dict(r) for r in c.execute('SELECT p.id,p.shop_id,s.name shop,p.reference,p.amount,p.created FROM cash_payments p JOIN shops s ON s.id=p.shop_id ORDER BY p.id DESC LIMIT 50 OFFSET ?',(offset,))]
   operations=[dict(r) for r in c.execute('SELECT o.id,o.shop_id,s.name shop,o.action,o.details,o.created FROM admin_operations o LEFT JOIN shops s ON s.id=o.shop_id ORDER BY o.id DESC LIMIT 50 OFFSET ?',(offset,))]
  return jsonify(payments=payments,operations=operations,offset=offset)
 @app.get('/api/admin/photo/<ident>')
 def subscription_photo(ident):
  with db() as c:
   if not admin(c):return err('Administration requise',401)
   if not re.fullmatch(r'[a-f0-9]{32}',ident):return err('Photo introuvable',404)
   row=c.execute('SELECT image FROM storefront_photos WHERE id=?',(ident,)).fetchone()
   if not row:return err('Photo introuvable',404)
  response=send_file(io.BytesIO(row[0]),mimetype='image/jpeg',max_age=0)
  response.headers['Cache-Control']='no-store'
  return response
 @app.get('/api/admin/moderation')
 def subscription_moderation():
  with db() as c:
   if not admin(c):return err('Administration requise',401)
   sid=request.args.get('shop_id',type=int)
   where=' WHERE o.shop_id=?' if sid is not None else ''
   params=(sid,) if sid is not None else ()
   offers=[dict(r) for r in c.execute("SELECT 'storefront' kind,o.id,o.shop_id,s.name shop,o.title,o.starts,o.ends,o.active FROM storefront_offers o JOIN shops s ON s.id=o.shop_id"+where+' ORDER BY o.id DESC LIMIT 200',params)]
   offers += [dict(r) for r in c.execute("SELECT 'nearby' kind,o.id,o.shop_id,s.name shop,o.title,o.starts,o.ends,o.active FROM nearby_offers o JOIN shops s ON s.id=o.shop_id"+where+' ORDER BY o.id DESC LIMIT 200',params)]
   photos=[dict(r) for r in c.execute("SELECT p.id,p.shop_id,EXISTS(SELECT 1 FROM storefront_hidden_photos h WHERE h.photo_id=p.id) hidden FROM storefront_photos p"+(' WHERE p.shop_id=?' if sid is not None else '')+' ORDER BY p.id LIMIT 200',params)]
  return jsonify(offers=offers,photos=photos)
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
   journal(c,'login')
  session['admin_token']=token
  return jsonify(ok=True)
 @app.post('/api/admin/logout')
 def subscription_logout():
  token=session.pop('admin_token',None)
  if isinstance(token,str):
   with db() as c:
    if c.execute('DELETE FROM admin_sessions WHERE digest=?',(digest(token),)).rowcount:journal(c,'logout')
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
    end=(max(today(),date.fromisoformat(t['paid_until']) if t['paid_until'] else today())+timedelta(days=30)).isoformat()
    c.execute('INSERT INTO cash_payments(shop_id,reference,amount) VALUES(?,?,19000)',(sid,ref))
    c.execute("UPDATE subscriptions SET paid_until=?,status='active' WHERE shop_id=?",(end,sid))
   elif action=='block':
    c.execute("UPDATE subscriptions SET status='blocked' WHERE shop_id=?",(sid,))
    c.execute('DELETE FROM merchant_sessions WHERE user_id IN (SELECT id FROM users WHERE shop_id=?)',(sid,))
   elif action=='activate':
    if t['paid_until']<=today().isoformat() or not c.execute('SELECT 1 FROM nearby_locations WHERE shop_id=? AND location_confirmed=1',(sid,)).fetchone():return err('Paiement valide et emplacement requis')
    c.execute("UPDATE subscriptions SET status='active' WHERE shop_id=?",(sid,))
   elif action=='profile':
    name=p.get('name');city=p.get('city');category=p.get('category');detail=p.get('category_detail','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=80 or not isinstance(city,str) or not 1<=len(city.strip())<=80 or category not in CATEGORIES or not isinstance(detail,str) or len(detail)>80:return err('Nom, ville et categorie valides requis')
    detail=detail.strip() if category=='other' else ''
    if category=='other' and not detail:return err('Precisez le type d etablissement')
    c.execute('UPDATE shops SET name=?,city=? WHERE id=?',(name.strip(),city.strip(),sid))
    c.execute('UPDATE subscriptions SET category=?,category_detail=? WHERE shop_id=?',(category,detail,sid))
   elif action=='moderate_photo':
    photo=p.get('photo_id');hidden=p.get('hidden')
    if not isinstance(photo,str) or not re.fullmatch(r'[a-f0-9]{32}',photo) or type(hidden)is not bool:return err('Photo ou statut invalide')
    if not c.execute('SELECT 1 FROM storefront_photos WHERE id=? AND shop_id=?',(photo,sid)).fetchone():return err('Photo introuvable',404)
    if hidden:c.execute('INSERT OR IGNORE INTO storefront_hidden_photos VALUES(?,?)',(photo,sid))
    else:c.execute('DELETE FROM storefront_hidden_photos WHERE photo_id=? AND shop_id=?',(photo,sid))
   elif action=='moderate_offer':
    kind=p.get('kind');oid=p.get('offer_id');active=p.get('active')
    if kind not in ('storefront','nearby') or type(oid)is not int or type(active)is not bool:return err('Offre ou statut invalide')
    table={'storefront':'storefront_offers','nearby':'nearby_offers'}[kind]
    if not c.execute('UPDATE '+table+' SET active=? WHERE id=? AND shop_id=?',(int(active),oid,sid)).rowcount:return err('Offre introuvable',404)
   elif action=='radius':
    r=p.get('radius')
    if type(r)is not int or not 100<=r<=10000:return err('Rayon entre 100 et 10000 metres')
    c.execute('UPDATE subscriptions SET radius=? WHERE shop_id=?',(r,sid))
   elif action=='offer_radius':
    r=p.get('radius');oid=p.get('offer_id')
    if type(oid)is not int or (r is not None and (type(r)is not int or not 100<=r<=10000)):return err('Rayon invalide')
    if not c.execute('UPDATE nearby_offers SET radius_override=? WHERE id=? AND shop_id=?',(r,oid,sid)).rowcount:return err('Offre introuvable',404)
   else:return err('Action invalide')
   details={}
   if action=='cash':details={'payment_reference':ref,'amount_millimes':19000,'paid_until':end}
   elif action=='profile':details={'category':category}
   elif action in ('radius','offer_radius'):details={'radius':r,**({'offer_id':oid} if action=='offer_radius' else {})}
   elif action=='moderate_photo':details={'photo_id':photo,'hidden':hidden}
   elif action=='moderate_offer':details={'kind':kind,'offer_id':oid,'active':active}
   journal(c,action,sid,details)
  return jsonify(ok=True)
