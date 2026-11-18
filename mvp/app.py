from flask import Flask, request, jsonify, session, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
import sqlite3, secrets, json, re, os
from datetime import datetime, date
ROOT=Path(__file__).parent; DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
key=DATA/'secret'; key.write_text(secrets.token_hex(32)) if not key.exists() else None
app=Flask(__name__,static_folder='static')
app.config.update(SECRET_KEY=key.read_text(),SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',MAX_CONTENT_LENGTH=32768)
def db():
 c=sqlite3.connect(DATA/'tunibiz.sqlite',timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS shops(id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL,name TEXT NOT NULL,city TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),email TEXT UNIQUE,password TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),name TEXT,category TEXT,price INTEGER CHECK(price>=0),active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),customer TEXT,table_no TEXT,total INTEGER,status TEXT DEFAULT 'new',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS order_lines(id INTEGER PRIMARY KEY,order_id INTEGER REFERENCES orders(id),name TEXT,qty INTEGER,unit INTEGER);
  CREATE TABLE IF NOT EXISTS reservations(id INTEGER PRIMARY KEY,shop_id INTEGER REFERENCES shops(id),customer TEXT,phone TEXT,day TEXT,slot TEXT,guests INTEGER,status TEXT DEFAULT 'pending',created TEXT DEFAULT CURRENT_TIMESTAMP);
  ''')
  if not c.execute('SELECT 1 FROM shops').fetchone():
   sid=c.execute("INSERT INTO shops(slug,name,city) VALUES('demo','Maison Café · Démo','Tunisie')").lastrowid
   pw=secrets.token_urlsafe(12); c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,'demo@tunibiz.local',generate_password_hash(pw)))
   (DATA/'demo-login.txt').write_text('Compte de test local uniquement\nEmail: demo@tunibiz.local\nMot de passe: '+pw+'\n',encoding='utf-8')
   c.executemany('INSERT INTO items(shop_id,name,category,price) VALUES(?,?,?,?)',[(sid,'Espresso','Cafés',3500),(sid,'Cappuccino','Cafés',5500),(sid,'Citronnade','Boissons',6500),(sid,'Croissant','Snacks',4500),(sid,'Sandwich poulet','Snacks',12000)])
init()
def err(msg,status=400):return jsonify(error=msg),status
def payload():return request.get_json(silent=True) or {}
def clean(x,n=80):return str(x or '').strip()[:n]
def merchant():
 if not session.get('shop'):abort(401)
 return session['shop']
def rows(c,q,p=()):return [dict(x) for x in c.execute(q,p)]
@app.errorhandler(401)
def unauth(e):return err('Connexion requise',401)
@app.errorhandler(404)
def missing(e):return err('Introuvable',404)
@app.before_request
def csrf():
 if request.method=='POST' and (not session.get('csrf') or not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session['csrf'])):return err('Session invalide, rechargez la page',403)
@app.after_request
def security(r):
 r.headers['X-Content-Type-Options']='nosniff';r.headers['Referrer-Policy']='same-origin';r.headers['X-Frame-Options']='DENY'
 if request.path.startswith('/api'):r.headers['Cache-Control']='no-store'
 return r
@app.get('/')
def relationship_home():return send_from_directory(app.static_folder,'relationship.html')
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
 return jsonify(csrf=session['csrf'],authenticated=bool(session.get('shop')))
@app.post('/api/login')
def login():
 p=payload()
 with db() as c:u=c.execute('SELECT * FROM users WHERE email=?',(clean(p.get('email')).lower(),)).fetchone()
 if not u or not check_password_hash(u['password'],str(p.get('password',''))[:200]):return err('Identifiants incorrects',401)
 session['shop']=u['shop_id'];return jsonify(ok=True)
@app.post('/api/logout')
def logout():
 session.pop('shop',None);return jsonify(ok=True)
@app.get('/api/menu/<slug>')
def menu(slug):
 with db() as c:
  shop=c.execute('SELECT * FROM shops WHERE slug=?',(slug,)).fetchone()
  if not shop:return err('Commerce introuvable',404)
  return jsonify(shop=dict(shop),items=rows(c,'SELECT id,name,category,price FROM items WHERE shop_id=? AND active=1 ORDER BY category,id',(shop['id'],)))
@app.post('/api/menu/<slug>/order')
def order(slug):
 p=payload();cart=p.get('cart');name=clean(p.get('customer'));table=clean(p.get('table'),20)
 if not name or not isinstance(cart,list) or not 1<=len(cart)<=30:return err('Nom et panier requis')
 with db() as c:
  shop=c.execute('SELECT id FROM shops WHERE slug=?',(slug,)).fetchone()
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
  if date.fromisoformat(day)<date.today():raise ValueError()
  datetime.strptime(slot,'%H:%M')
 except ValueError:return err('Date ou heure incorrecte')
 if not name or not re.fullmatch(r'[+0-9 ()-]{8,25}',phone) or type(guests)is not int or not 1<=guests<=30:return err('Vérifiez les informations')
 with db() as c:
  shop=c.execute('SELECT id FROM shops WHERE slug=?',(slug,)).fetchone()
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
if __name__=='__main__':
 print('TUNIBIZ local preview: http://127.0.0.1:8877',flush=True)
 app.run(host='127.0.0.1',port=8877,debug=False)
