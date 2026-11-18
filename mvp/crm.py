"""TUNIBIZ CRM + Loyalty, local MVP. Amounts in millimes; 1 point / whole DT."""
import secrets, hashlib, re
from datetime import date, timedelta
from flask import request, jsonify, session, send_from_directory
def install(app, db, payload, clean, merchant, err):
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS crm_customers(id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),name TEXT NOT NULL,phone TEXT NOT NULL DEFAULT '',consent INTEGER NOT NULL DEFAULT 0,code_hash TEXT UNIQUE NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS loyalty_ledger(id INTEGER PRIMARY KEY,customer_id INTEGER NOT NULL REFERENCES crm_customers(id),kind TEXT NOT NULL,amount INTEGER NOT NULL DEFAULT 0,points INTEGER NOT NULL,label TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP,request_key TEXT UNIQUE);
  CREATE TABLE IF NOT EXISTS campaigns(id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),title TEXT NOT NULL,description TEXT NOT NULL,segment TEXT NOT NULL,starts TEXT NOT NULL,ends TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
  CREATE TABLE IF NOT EXISTS rewards(id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),title TEXT NOT NULL,cost INTEGER NOT NULL CHECK(cost>0),active INTEGER NOT NULL DEFAULT 1);
  """)
  cols={r['name'] for r in c.execute('PRAGMA table_info(rewards)')}
  if 'visual' not in cols:c.execute("ALTER TABLE rewards ADD COLUMN visual TEXT NOT NULL DEFAULT 'general'")
  if 'description' not in cols:c.execute("ALTER TABLE rewards ADD COLUMN description TEXT NOT NULL DEFAULT ''")
 def digest(s):return hashlib.sha256(s.encode()).hexdigest()
 def token():return secrets.token_urlsafe(24)
 def listrows(c,sql,args=()):return [dict(r) for r in c.execute(sql,args)]
 def customers(c,sid):
  return listrows(c,"SELECT a.id,a.name,a.phone,a.consent,a.created,COALESCE(SUM(l.points),0) points,COALESCE(SUM(CASE WHEN l.kind='purchase' THEN l.amount ELSE 0 END),0) spent,COUNT(CASE WHEN l.kind='purchase' THEN 1 END) purchases,MAX(CASE WHEN l.kind='purchase' THEN l.created END) last_purchase FROM crm_customers a LEFT JOIN loyalty_ledger l ON l.customer_id=a.id WHERE a.shop_id=? GROUP BY a.id ORDER BY a.id DESC",(sid,))
 def segment_ok(a,segment):
  if segment=='all':return True
  if segment=='vip':return a['spent']>=100000
  if segment=='inactive':return bool(a['last_purchase'] and a['last_purchase'][:10]<(date.today()-timedelta(days=30)).isoformat())
  return False
 def campaigns(c,sid):return listrows(c,'SELECT * FROM campaigns WHERE shop_id=? ORDER BY id DESC',(sid,))
 def rewards(c,sid):return listrows(c,'SELECT * FROM rewards WHERE shop_id=? ORDER BY id DESC',(sid,))
 def getcustomer(c,sid,cid):return next((a for a in customers(c,sid) if a['id']==cid),None)
 @app.get('/crm')
 @app.get('/loyalty')
 def crm_page():return send_from_directory(app.static_folder,'crm.html')
 @app.get('/api/crm')
 def crm():
  sid=merchant()
  with db() as c:
   a=customers(c,sid);cs=campaigns(c,sid)
   for x in cs:x['audience']=sum(1 for z in a if z['consent'] and segment_ok(z,x['segment']))
   return jsonify(customers=a,campaigns=cs,rewards=rewards(c,sid),stats={'customers':len(a),'consented':sum(z['consent'] for z in a),'points':sum(z['points'] for z in a),'spent':sum(z['spent'] for z in a)})
 @app.post('/api/crm/customer')
 def customer_create():
  sid=merchant();p=payload();n=clean(p.get('name'));phone=clean(p.get('phone'),25);consent=p.get('consent') is True
  if not n or (phone and not re.fullmatch(r'[0-9+ ()-]{8,25}',phone)):return err('Nom ou téléphone invalide')
  code=token()
  with db() as c:
   cid=c.execute('INSERT INTO crm_customers(shop_id,name,phone,consent,code_hash) VALUES(?,?,?,?,?)',(sid,n,phone,int(consent),digest(code))).lastrowid
  return jsonify(id=cid,code=code),201
 @app.post('/api/crm/customer/consent')
 def consent():
  sid=merchant();p=payload()
  if type(p.get('id')) is not int or type(p.get('consent')) is not bool:return err('Données invalides')
  with db() as c:
   if not c.execute('UPDATE crm_customers SET consent=? WHERE shop_id=? AND id=?',(int(p['consent']),sid,p['id'])).rowcount:return err('Client introuvable',404)
  return jsonify(ok=True)
 @app.post('/api/crm/customer/reset')
 def reset():
  sid=merchant();p=payload();code=token()
  with db() as c:
   if not c.execute('UPDATE crm_customers SET code_hash=? WHERE shop_id=? AND id=?',(digest(code),sid,p.get('id'))).rowcount:return err('Client introuvable',404)
  return jsonify(code=code)
 @app.get('/api/crm/customer/<int:cid>')
 def detail(cid):
  sid=merchant()
  with db() as c:
   a=getcustomer(c,sid,cid)
   if not a:return err('Client introuvable',404)
   return jsonify(customer=a,history=listrows(c,'SELECT kind,amount,points,label,created FROM loyalty_ledger WHERE customer_id=? ORDER BY id DESC LIMIT 200',(cid,)))
 @app.post('/api/crm/purchase')
 def purchase():
  sid=merchant();p=payload();cid=p.get('id');amount=p.get('amount');label=clean(p.get('label')) or 'Achat';key=clean(p.get('key'),64)
  if type(cid)is not int or type(amount)is not int or not 1<=amount<=10000000 or not key:return err('Achat invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not getcustomer(c,sid,cid):return err('Client introuvable',404)
   existing=c.execute('SELECT customer_id,amount FROM loyalty_ledger WHERE request_key=?',(key,)).fetchone()
   if existing:
    if existing['customer_id']==cid and existing['amount']==amount:return jsonify(ok=True,duplicate=True)
    return err('Référence déjà utilisée',409)
   c.execute("INSERT INTO loyalty_ledger(customer_id,kind,amount,points,label,request_key) VALUES(?,'purchase',?,?,?,?)",(cid,amount,amount//1000,label,key))
  return jsonify(ok=True,points=amount//1000),201
 @app.post('/api/crm/campaign')
 def campaign():
  sid=merchant();p=payload();title=clean(p.get('title'));desc=clean(p.get('description'),500);seg=p.get('segment');start=clean(p.get('starts'),10);end=clean(p.get('ends'),10)
  try:
   if date.fromisoformat(end)<date.fromisoformat(start):raise ValueError()
  except ValueError:return err('Dates invalides')
  if not title or not desc or seg not in ('all','vip','inactive'):return err('Campagne invalide')
  with db() as c:i=c.execute('INSERT INTO campaigns(shop_id,title,description,segment,starts,ends) VALUES(?,?,?,?,?,?)',(sid,title,desc,seg,start,end)).lastrowid
  return jsonify(id=i),201
 @app.post('/api/crm/campaign/stop')
 def stop():
  sid=merchant()
  with db() as c:
   if not c.execute('UPDATE campaigns SET active=0 WHERE shop_id=? AND id=?',(sid,payload().get('id'))).rowcount:return err('Campagne introuvable',404)
  return jsonify(ok=True)
 @app.post('/api/crm/reward')
 def reward():
  sid=merchant();p=payload();title=clean(p.get('title'));cost=p.get('cost');visual=p.get('visual','general');description=clean(p.get('description'),240)
  if not title or type(cost)is not int or not 1<=cost<=100000 or visual not in ('general','coffee','restaurant','bakery','drinks','shopping'):return err('Récompense invalide')
  with db() as c:i=c.execute('INSERT INTO rewards(shop_id,title,cost,visual,description) VALUES(?,?,?,?,?)',(sid,title,cost,visual,description)).lastrowid
  return jsonify(id=i),201
 @app.post('/api/crm/redeem')
 def redeem():
  sid=merchant();p=payload();cid=p.get('id');rid=p.get('reward');key=clean(p.get('key'),64)
  if type(cid)is not int or type(rid)is not int or not key:return err('Données invalides')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   a=getcustomer(c,sid,cid);r=c.execute('SELECT * FROM rewards WHERE id=? AND shop_id=? AND active=1',(rid,sid)).fetchone()
   if not a or not r:return err('Client ou récompense introuvable',404)
   old=c.execute('SELECT customer_id,kind,label FROM loyalty_ledger WHERE request_key=?',(key,)).fetchone()
   if old:
    if old['customer_id']==cid and old['kind']=='redeem' and old['label']==r['title']:return jsonify(ok=True,duplicate=True)
    return err('Référence déjà utilisée',409)
   if a['points']<r['cost']:return err('Solde de points insuffisant')
   c.execute("INSERT INTO loyalty_ledger(customer_id,kind,points,label,request_key) VALUES(?,'redeem',?,?,?)",(cid,-r['cost'],r['title'],key))
  return jsonify(ok=True),201
 @app.post('/api/loyalty/login')
 def login_card():
  code=clean(payload().get('code'),100)
  with db() as c:a=c.execute('SELECT id,code_hash FROM crm_customers WHERE code_hash=?',(digest(code),)).fetchone()
  if not a:return err('Code de carte incorrect',401)
  session.pop('wallet_card',None);session['card']=a['id'];session['card_hash']=a['code_hash'];return jsonify(ok=True)
 @app.post('/api/loyalty/logout')
 def card_logout():
  session.pop('wallet_card',None);session.pop('card',None);session.pop('card_hash',None);return jsonify(ok=True)
 @app.get('/api/loyalty')
 def card():
  with db() as c:
   row=c.execute('SELECT id,shop_id FROM crm_customers WHERE id=? AND code_hash=?',(session.get('card'),session.get('card_hash'))).fetchone()
   if not row:return err('Connectez votre carte',401)
   a=getcustomer(c,row['shop_id'],row['id']);today=date.today().isoformat()
   cs=[{k:x[k] for k in ('id','title','description','ends')} for x in campaigns(c,row['shop_id']) if a['consent'] and x['active'] and x['starts']<=today<=x['ends'] and segment_ok(a,x['segment'])]
   rs=[{k:x[k] for k in ('id','title','cost','visual','description')} for x in rewards(c,row['shop_id']) if x['active']]
   shop=c.execute('SELECT name FROM shops WHERE id=?',(row['shop_id'],)).fetchone()['name']
   return jsonify(customer={k:a[k] for k in ('name','points','spent','purchases','consent')},shop=shop,campaigns=cs,rewards=rs,history=listrows(c,'SELECT kind,amount,points,label,created FROM loyalty_ledger WHERE customer_id=? ORDER BY id DESC LIMIT 100',(row['id'],)))
 @app.post('/api/loyalty/optout')
 def optout():
  with db() as c:
   if not c.execute('UPDATE crm_customers SET consent=0 WHERE id=? AND code_hash=?',(session.get('card'),session.get('card_hash'))).rowcount:return err('Connexion requise',401)
  return jsonify(ok=True)
