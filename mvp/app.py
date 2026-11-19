from business_clock import today as business_today
from flask import Flask, request, jsonify, session, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
import sqlite3, secrets, json, re, os, hashlib, time
from datetime import datetime, date, timedelta
ROOT=Path(__file__).parent
PRODUCTION=os.environ.get('TUNIBIZ_ENV')=='production'
if PRODUCTION:
 secret=os.environ.get('TUNIBIZ_SECRET','')
 data_dir=os.environ.get('TUNIBIZ_DATA_DIR','')
 if len(secret)<48 or not data_dir or not Path(data_dir).is_absolute():raise RuntimeError('Production requires TUNIBIZ_SECRET (48+ chars) and absolute TUNIBIZ_DATA_DIR')
 DATA=Path(data_dir)
else:
 DATA=ROOT/'data'
DATA.mkdir(parents=True,exist_ok=True)
if not PRODUCTION:
 key=DATA/'secret';key.write_text(secrets.token_hex(32)) if not key.exists() else None
 secret=key.read_text()
app=Flask(__name__,static_folder='static')
app.config.update(SECRET_KEY=secret,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SECURE=PRODUCTION,SESSION_COOKIE_SAMESITE='Lax',MAX_CONTENT_LENGTH=32768,PERMANENT_SESSION_LIFETIME=timedelta(days=30),SESSION_REFRESH_EACH_REQUEST=False)
class ManagedConnection(sqlite3.Connection):
 def __exit__(self,*args):
  try:return super().__exit__(*args)
  finally:self.close()

def db():
 c=sqlite3.connect(DATA/'tunibiz.sqlite',timeout=10,factory=ManagedConnection)
 c.row_factory=sqlite3.Row
 c.execute('PRAGMA foreign_keys=ON')
 c.execute('PRAGMA busy_timeout=10000')
 return c
def init():
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS shops(id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL,name TEXT NOT NULL,city TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),email TEXT UNIQUE,password TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS merchant_sessions(digest TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),name TEXT,category TEXT,price INTEGER CHECK(price>=0),active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),customer TEXT,table_no TEXT,total INTEGER,status TEXT DEFAULT 'new',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS order_lines(id INTEGER PRIMARY KEY,order_id INTEGER REFERENCES orders(id),name TEXT,qty INTEGER,unit INTEGER);
  CREATE TABLE IF NOT EXISTS reservations(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),customer TEXT,phone TEXT,day TEXT,slot TEXT,guests INTEGER,status TEXT DEFAULT 'pending',created TEXT DEFAULT CURRENT_TIMESTAMP);
  ''')
  if PRODUCTION and c.execute("SELECT 1 FROM users WHERE email='demo@tunibiz.local'").fetchone():raise RuntimeError('Remove demo account before production')
  if not PRODUCTION and not c.execute('SELECT 1 FROM shops').fetchone():
   sid=c.execute("INSERT INTO shops(slug,name,city) VALUES('demo','Maison Café · Démo','Tunisie')").lastrowid
   pw=secrets.token_urlsafe(12); c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'demo@tunibiz.local',generate_password_hash(pw)))
   (DATA/'demo-login.txt').write_text('Compte de test local uniquement\nEmail: demo@tunibiz.local\nMot de passe: '+pw+'\n',encoding='utf-8')
   c.executemany('INSERT INTO items(shop_id,name,category,price) VALUES(?,?,?,?)',[(sid,'Espresso','Cafés',3500),(sid,'Cappuccino','Cafés',5500),(sid,'Citronnade','Boissons',6500),(sid,'Croissant','Snacks',4500),(sid,'Sandwich poulet','Snacks',12000)])
init()
def throttle(kind,subject,max_attempts):
 import time
 window=int(time.time())//900
 with db() as c:
  c.execute('BEGIN IMMEDIATE')
  c.execute('DELETE FROM wallet_attempts WHERE window<?',(window-1,))
  r=c.execute('SELECT window,count FROM wallet_attempts WHERE kind=? AND subject=?',(kind,subject)).fetchone()
  if r and r['window']==window and r['count']>=max_attempts:return False
  c.execute('INSERT INTO wallet_attempts(kind,subject,window,count) VALUES(?,?,?,1) ON CONFLICT(kind,subject) DO UPDATE SET count=CASE WHEN window=excluded.window THEN count+1 ELSE 1 END,window=excluded.window',(kind,subject,window))
 return True
def err(msg,status=400):return jsonify(error=msg),status
def payload():
 p=request.get_json(silent=True);return p if isinstance(p,dict) else {}
def clean(x,n=80):return str(x or '').strip()[:n]
def merchant_digest(token):return hashlib.sha256(token.encode()).hexdigest()
def merchant_identity():
 token=session.get('merchant_token')
 if not isinstance(token,str):return None
 with db() as c:
  u=c.execute("SELECT u.shop_id FROM merchant_sessions s JOIN users u ON u.id=s.user_id JOIN subscriptions t ON t.shop_id=u.shop_id WHERE s.digest=? AND s.expires>? AND t.status='active' AND t.paid_until>date('now','+1 hour')",(merchant_digest(token),int(time.time()))).fetchone()
 return u['shop_id'] if u else None
def merchant(connection=None):
 if connection is not None:
  token=session.get('merchant_token')
  u=connection.execute("SELECT u.shop_id FROM merchant_sessions s JOIN users u ON u.id=s.user_id JOIN subscriptions t ON t.shop_id=u.shop_id WHERE s.digest=? AND s.expires>? AND t.status='active' AND t.paid_until>date('now','+1 hour')",(merchant_digest(token),int(time.time()))).fetchone() if isinstance(token,str) else None
  if not u:abort(401)
  return u['shop_id']
 sid=merchant_identity()
 if not sid:abort(401)
 return sid

def rows(c,q,p=()):return [dict(x) for x in c.execute(q,p)]
@app.errorhandler(401)
def unauth(e):return err('Connexion requise',401)
@app.errorhandler(404)
def missing(e):return err('Introuvable',404)
@app.before_request
def csrf():
 if request.path in ('/api/storefront/photo','/api/commerce/sponsor/photo'):
  request.max_content_length=400000

 if request.method=='POST' and (not session.get('csrf') or not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session['csrf'])):return err('Session invalide, rechargez la page',403)
@app.after_request
def security(r):
 r.headers['X-Content-Type-Options']='nosniff';r.headers['Referrer-Policy']='strict-origin-when-cross-origin' if request.path in ('/nearby','/merchant-register') else 'same-origin';r.headers['X-Frame-Options']='DENY'
 if PRODUCTION:r.headers['Strict-Transport-Security']='max-age=31536000'
 if request.path.startswith('/api') or request.path=='/reset-password':r.headers['Cache-Control']='no-store'
 if request.path=='/reset-password':r.headers['Referrer-Policy']='no-referrer'
 return r
@app.get('/')
def relationship_home():return send_from_directory(app.static_folder,'home-premium.html')
@app.get('/solutions')
def solutions_page():return send_from_directory(app.static_folder,'relationship.html')
@app.get('/download')
def download_page():return send_from_directory(app.static_folder,'download.html')
@app.get('/account-deletion')
def account_deletion():return send_from_directory(app.static_folder,'account-deletion.html')
@app.get('/privacy')
def privacy():return send_from_directory(app.static_folder,'privacy.html')
@app.get('/business')
@app.get('/menu/<slug>')
def page(slug=None):return send_from_directory(app.static_folder,'index.html')
@app.get('/manifest.webmanifest')
def manifest():return send_from_directory(app.static_folder,'manifest.webmanifest')
@app.get('/sw.js')
def sw():return send_from_directory(app.static_folder,'sw.js')
@app.get('/api/session')
def who():
 session.setdefault('csrf',secrets.token_urlsafe(24))
 return jsonify(csrf=session['csrf'],authenticated=bool(merchant_identity()))
@app.post('/api/login')
def login():
 if not throttle('merchant_login',request.remote_addr or 'local',30):return err('Trop de tentatives',429)
 p=payload()
 with db() as c:u=c.execute('SELECT * FROM users WHERE email=?',(clean(p.get('email')).lower(),)).fetchone()
 if not u or not check_password_hash(u['password'],str(p.get('password',''))[:200]):return err('Identifiants incorrects',401)
 with db() as c:
  if not c.execute("SELECT 1 FROM subscriptions WHERE shop_id=? AND status='active' AND paid_until>date('now','+1 hour')",(u['shop_id'],)).fetchone():return err('Compte en attente, bloque ou abonnement expire. Contactez TUNIBIZ.',403)
 token=secrets.token_urlsafe(32);old=session.get('merchant_token');now=int(time.time())
 with db() as c:
  c.execute('DELETE FROM merchant_sessions WHERE expires<=?',(now,))
  if isinstance(old,str):c.execute('DELETE FROM merchant_sessions WHERE digest=?',(merchant_digest(old),))
  c.execute('INSERT INTO merchant_sessions VALUES(?,?,?)',(merchant_digest(token),u['id'],now+30*86400))
 session.pop('shop',None);session.pop('merchant_until',None);session['merchant_token']=token;session.permanent=True
 return jsonify(ok=True)
@app.post('/api/logout')
def logout():
 token=session.pop('merchant_token',None)
 if isinstance(token,str):
  with db() as c:c.execute('DELETE FROM merchant_sessions WHERE digest=?',(merchant_digest(token),))
 session.pop('shop',None);session.pop('merchant_until',None)
 return jsonify(ok=True)
@app.get('/api/menu/<slug>')
def menu(slug):
 with db() as c:
  shop=c.execute("SELECT s.* FROM shops s JOIN subscriptions t ON t.shop_id=s.id WHERE s.slug=? AND t.status='active' AND t.paid_until>date('now','+1 hour')",(slug,)).fetchone()
  if not shop:return err('Commerce introuvable',404)
  return jsonify(shop=dict(shop),items=rows(c,'SELECT id,name,category,price FROM items WHERE shop_id=? AND active=1 ORDER BY category,id',(shop['id'],)))
@app.post('/api/menu/<slug>/order')
def order(slug):
 p=payload();cart=p.get('cart');name=clean(p.get('customer'));table=clean(p.get('table'),20)
 if not name or not isinstance(cart,list) or not 1<=len(cart)<=30:return err('Nom et panier requis')
 with db() as c:
  shop=c.execute("SELECT s.id FROM shops s JOIN subscriptions t ON t.shop_id=s.id WHERE s.slug=? AND t.status='active' AND t.paid_until>date('now','+1 hour')",(slug,)).fetchone()
  if not shop:return err('Commerce introuvable',404)
  lines=[];total=0;seen=set()
  for x in cart:
   if not isinstance(x,dict) or type(x.get('id')) is not int or type(x.get('qty')) is not int or not 1<=x['qty']<=20 or x['id'] in seen:return err('Panier invalide')
   seen.add(x['id']);item=c.execute('SELECT * FROM items WHERE id=? AND shop_id=? AND active=1',(x['id'],shop['id'])).fetchone()
   if not item:return err('Produit indisponible')
   total+=item['price']*x['qty'];lines.append((item['name'],x['qty'],item['price']))
  oid=c.execute('INSERT INTO orders(shop_id,customer,table_no,total) VALUES(?,?,?,?)',(shop['id'],name,table,total)).lastrowid
  c.executemany('INSERT INTO order_lines(order_id,name,qty,unit) VALUES(?,?,?,?)',[(oid,*x) for x in lines])
 return jsonify(id=oid,total=total,status='new'),201
@app.post('/api/menu/<slug>/reserve')
def reserve(slug):
 p=payload();name=clean(p.get('customer'));phone=clean(p.get('phone'),25);day=clean(p.get('day'),10);slot=clean(p.get('slot'),5);guests=p.get('guests')
 try:
  if date.fromisoformat(day)<business_today():raise ValueError()
  datetime.strptime(slot,'%H:%M')
 except ValueError:return err('Date ou heure incorrecte')
 if not name or not re.fullmatch(r'[+0-9 ()-]{8,25}',phone) or type(guests)is not int or not 1<=guests<=30:return err('Vérifiez les informations')
 with db() as c:
  shop=c.execute("SELECT s.id FROM shops s JOIN subscriptions t ON t.shop_id=s.id WHERE s.slug=? AND t.status='active' AND t.paid_until>date('now','+1 hour')",(slug,)).fetchone()
  if not shop:return err('Commerce introuvable',404)
  oid=c.execute('INSERT INTO reservations(shop_id,customer,phone,day,slot,guests) VALUES(?,?,?,?,?,?)',(shop['id'],name,phone,day,slot,guests)).lastrowid
 return jsonify(id=oid,status='pending'),201
@app.get('/api/business')
def business():
 sid=merchant()
 with db() as c:
  shop=dict(c.execute('SELECT * FROM shops WHERE id=?',(sid,)).fetchone())
  orders=rows(c,'SELECT * FROM orders WHERE shop_id=? ORDER BY id DESC LIMIT 100',(sid,))
  for o in orders:o['lines']=rows(c,'SELECT name,qty,unit FROM order_lines WHERE order_id=?',(o['id'],))
  stats=dict(c.execute("SELECT COUNT(*) orders,COALESCE(SUM(CASE WHEN status='completed' THEN total ELSE 0 END),0) sales,COALESCE(SUM(CASE WHEN status='new' THEN 1 ELSE 0 END),0) pending FROM orders WHERE shop_id=?",(sid,)).fetchone())
  reservations=rows(c,'SELECT * FROM reservations WHERE shop_id=? ORDER BY day,slot LIMIT 100',(sid,))
  items=rows(c,'SELECT * FROM items WHERE shop_id=? ORDER BY id DESC',(sid,))
 return jsonify(shop=shop,orders=orders,stats=stats,reservations=reservations,items=items)
@app.post('/api/business/item')
def item():
 sid=merchant();p=payload();name=clean(p.get('name'));cat=clean(p.get('category'),40);price=p.get('price');iid=p.get('id')
 if not name or not cat or type(price)is not int or not 0<=price<=10000000:return err('Produit ou prix invalide')
 with db() as c:
  c.execute('BEGIN IMMEDIATE');merchant(c)
  if iid:
   if not c.execute('UPDATE items SET name=?,category=?,price=?,active=? WHERE id=? AND shop_id=?',(name,cat,price,int(bool(p.get('active',True))),iid,sid)).rowcount:return err('Produit introuvable',404)
  else:c.execute('INSERT INTO items(shop_id,name,category,price) VALUES(?,?,?,?)',(sid,name,cat,price))
 return jsonify(ok=True)
@app.post('/api/business/status')
def status():
 sid=merchant();p=payload();kind=p.get('kind');iid=p.get('id');new=p.get('status')
 allowed={'orders':{'new':['accepted','cancelled'],'accepted':['completed','cancelled']},'reservations':{'pending':['confirmed','cancelled'],'confirmed':['cancelled']}}
 if kind not in allowed or type(iid)is not int:return err('Action invalide')
 with db() as c:
  c.execute('BEGIN IMMEDIATE');merchant(c)
  old=c.execute(f'SELECT status FROM {kind} WHERE id=? AND shop_id=?',(iid,sid)).fetchone()
  if not old:return err('Introuvable',404)
  if new not in allowed[kind].get(old['status'],[]):return err('Transition invalide')
  c.execute(f'UPDATE {kind} SET status=? WHERE id=? AND shop_id=?',(new,iid,sid))
 return jsonify(ok=True)
from crm import install as install_crm
install_crm(app, db, payload, clean, merchant, err)
from leads import install as install_leads
install_leads(app, db, payload, clean, merchant, err)
from nearby import install as install_nearby
install_nearby(app, db, payload, clean, merchant, err)
from loyalty_qr import install as install_qr
install_qr(app,db,payload,merchant,err)
from wallet import install as install_wallet
install_wallet(app,db,payload,clean,err)
from subscriptions import install as install_subscriptions
install_subscriptions(app,db,payload,clean,err,throttle,PRODUCTION)
from google_identity import install as install_google
install_google(app,db,payload,err,throttle)
from analytics import install as install_analytics
install_analytics(app,db,payload,err)
from password_recovery import install as install_recovery
install_recovery(app,db,payload,err,throttle)
from store_scan import install as install_store_scan
install_store_scan(app,db,payload,merchant,err)
from app_release import install as install_release
install_release(app,db,payload,err)
from storefront import install as install_storefront
install_storefront(app,db,payload,clean,merchant,err)
from verification import install as install_verification
install_verification(app,db,payload,err,throttle,PRODUCTION)
from pilot_security import install as install_pilot_security
install_pilot_security(app,db,err,throttle)
from push_notifications import install as install_push_notifications
install_push_notifications(app,db,payload,err,throttle)
from commerce import install as install_commerce
install_commerce(app,db,payload,clean,merchant,err,throttle)
if __name__=='__main__':
 if PRODUCTION:raise RuntimeError('Use a production WSGI server, not Flask development server')
 print('TUNIBIZ local preview: http://127.0.0.1:8877',flush=True)
 app.run(host='127.0.0.1',port=8877,debug=False)
