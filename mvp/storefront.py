"""Public active storefronts, bounded merchant photos, dated offers and single-use coupons."""
import base64,binascii,hashlib,io,re,secrets,time
from datetime import date
from flask import jsonify,request,session,send_file,send_from_directory
from PIL import Image,ImageOps

ACTIVE="t.status='active' AND t.paid_until>date('now','+1 hour')"
TODAY="date('now','+1 hour')"
def install(app,db,payload,clean,merchant,err):
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS storefront_photos(id TEXT PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),image BLOB NOT NULL);
  CREATE TABLE IF NOT EXISTS storefront_profiles(shop_id INTEGER PRIMARY KEY REFERENCES shops(id),description TEXT NOT NULL DEFAULT '',cover TEXT REFERENCES storefront_photos(id));
  CREATE TABLE IF NOT EXISTS storefront_offers(id INTEGER PRIMARY KEY AUTOINCREMENT,shop_id INTEGER NOT NULL REFERENCES shops(id),kind TEXT NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL,starts TEXT NOT NULL,ends TEXT NOT NULL,old_price INTEGER,new_price INTEGER,discount INTEGER,photo TEXT REFERENCES storefront_photos(id),active INTEGER NOT NULL DEFAULT 1);
  CREATE TABLE IF NOT EXISTS storefront_coupons(code TEXT PRIMARY KEY,offer_id INTEGER NOT NULL REFERENCES storefront_offers(id),account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,used INTEGER,UNIQUE(offer_id,account_id));
  CREATE TABLE IF NOT EXISTS storefront_gallery(shop_id INTEGER NOT NULL REFERENCES shops(id),photo_id TEXT NOT NULL REFERENCES storefront_photos(id),position INTEGER NOT NULL,PRIMARY KEY(shop_id,photo_id));
  CREATE TABLE IF NOT EXISTS storefront_hidden_photos(photo_id TEXT PRIMARY KEY REFERENCES storefront_photos(id) ON DELETE CASCADE,shop_id INTEGER NOT NULL REFERENCES shops(id));
  CREATE TABLE IF NOT EXISTS storefront_favorites(account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,shop_id INTEGER NOT NULL REFERENCES shops(id),PRIMARY KEY(account_id,shop_id));
  CREATE INDEX IF NOT EXISTS storefront_offer_dates ON storefront_offers(shop_id,active,starts,ends);
  """)
  if 'hours' not in {r['name'] for r in c.execute('PRAGMA table_info(storefront_profiles)')}:c.execute("ALTER TABLE storefront_profiles ADD COLUMN hours TEXT NOT NULL DEFAULT ''")
 def account(c):
  t=session.get('wallet_token')
  return c.execute('SELECT account_id FROM wallet_sessions WHERE digest=? AND expires>?',(hashlib.sha256(t.encode()).hexdigest(),int(time.time()))).fetchone() if isinstance(t,str) else None
 def photo_owned(c,sid,p):
  return p is None or (isinstance(p,str) and c.execute('SELECT 1 FROM storefront_photos WHERE id=? AND shop_id=?',(p,sid)).fetchone())
 def profile(c,sid,public=False):
  p=dict(c.execute("""SELECT s.id,s.slug,s.name,s.city,t.category,t.category_detail,COALESCE(p.description,'') description,p.cover,COALESCE(p.hours,'') hours,l.address,l.lat,l.lon FROM shops s JOIN subscriptions t ON t.shop_id=s.id LEFT JOIN storefront_profiles p ON p.shop_id=s.id LEFT JOIN nearby_locations l ON l.shop_id=s.id WHERE s.id=?""",(sid,)).fetchone())
  p['gallery']=[r[0] for r in c.execute('SELECT photo_id FROM storefront_gallery WHERE shop_id=? ORDER BY position',(sid,))]
  if public:
   if p['cover'] and c.execute('SELECT 1 FROM storefront_hidden_photos WHERE photo_id=?',(p['cover'],)).fetchone():p['cover']=None
   hidden={r[0] for r in c.execute('SELECT photo_id FROM storefront_hidden_photos WHERE shop_id=?',(sid,))}
   p['gallery']=[g for g in p['gallery'] if g not in hidden]
  return p
 def offers(c,sid,public=False):
  extra=" AND active=1 AND starts<="+TODAY+" AND ends>="+TODAY if public else ""
  result=[dict(r) for r in c.execute("SELECT id,kind,title,description,starts,ends,old_price,new_price,discount,photo,active FROM storefront_offers WHERE shop_id=?"+extra+" ORDER BY id DESC",(sid,))]
  for o in result:
   if public and o['photo'] and c.execute('SELECT 1 FROM storefront_hidden_photos WHERE photo_id=?',(o['photo'],)).fetchone():o['photo']=None
   o['reduction_percent']=((o['old_price']-o['new_price'])*100)//o['old_price'] if o['kind']!='coupon' and o['old_price'] else o['discount']
  return result
 def active_shop(c,sid):
  return c.execute("SELECT 1 FROM subscriptions t WHERE t.shop_id=? AND "+ACTIVE,(sid,)).fetchone()
 @app.get('/stores')
 def sf_stores_page():return send_from_directory(app.static_folder,'storefront.html')
 @app.get('/storefront')
 def sf_merchant_page():return send_from_directory(app.static_folder,'storefront.html')
 @app.get('/api/stores')
 def sf_directory():
  with db() as c:
   a=account(c)
   rows=[dict(r) for r in c.execute("""SELECT s.id,s.slug,s.name,s.city,t.category,t.category_detail,p.cover FROM shops s JOIN subscriptions t ON t.shop_id=s.id LEFT JOIN storefront_profiles p ON p.shop_id=s.id WHERE """+ACTIVE+" ORDER BY s.name LIMIT 500")]
   joined={r[0] for r in c.execute('SELECT DISTINCT a.shop_id FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash WHERE w.account_id=?',(a[0],))} if a else set()
   hidden={r[0] for r in c.execute('SELECT photo_id FROM storefront_hidden_photos')}
   for row in rows:
    if row['cover'] in hidden:row['cover']=None
   favorites={r[0] for r in c.execute('SELECT shop_id FROM storefront_favorites WHERE account_id=?',(a[0],))} if a else set()
   return jsonify(stores=[{**r,'joined':r['id'] in joined,'favorite':r['id'] in favorites} for r in rows])
 @app.post('/api/stores/favorite')
 def sf_favorite():
  p=payload();sid=p.get('id');value=p.get('favorite')
  if type(sid)is not int or type(value)is not bool:return err('Commerce ou choix invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');a=account(c)
   if not a:return err('Connectez votre portefeuille',401)
   if not active_shop(c,sid):return err('Commerce indisponible',404)
   if value:c.execute('INSERT OR IGNORE INTO storefront_favorites VALUES(?,?)',(a[0],sid))
   else:c.execute('DELETE FROM storefront_favorites WHERE account_id=? AND shop_id=?',(a[0],sid))
  return jsonify(ok=True,favorite=value)
 @app.get('/api/stores/<int:sid>')
 def sf_store(sid):
  with db() as c:
   if not active_shop(c,sid):return err('Commerce indisponible',404)
   a=account(c);p=profile(c,sid,True);p['offers']=offers(c,sid,True)
   p['nearby']=[dict(r) for r in c.execute("SELECT id,title,description,starts,ends,category FROM nearby_offers WHERE shop_id=? AND active=1 AND starts<="+TODAY+" AND ends>="+TODAY,(sid,))]
   p['coupons']=[dict(r) for r in c.execute("SELECT q.offer_id,q.code,q.used FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE q.account_id=? AND o.shop_id=? AND o.active=1 AND o.starts<="+TODAY+" AND o.ends>="+TODAY,(a[0],sid))] if a else []
   p['favorite']=bool(a and c.execute('SELECT 1 FROM storefront_favorites WHERE account_id=? AND shop_id=?',(a[0],sid)).fetchone())
   p['points']=c.execute("SELECT COALESCE(SUM(l.points),0) FROM wallet_cards w JOIN crm_customers x ON x.id=w.customer_id AND x.code_hash=w.card_hash JOIN loyalty_ledger l ON l.customer_id=x.id WHERE w.account_id=? AND x.shop_id=?",(a[0],sid)).fetchone()[0] if a else None
   p['rewards']=[dict(r) for r in c.execute('SELECT id,title,cost,description,visual FROM rewards WHERE shop_id=? AND active=1 ORDER BY cost',(sid,))]
   return jsonify(p)
 @app.get('/api/storefront/manage')
 def sf_manage():
  sid=merchant()
  with db() as c:return jsonify(profile=profile(c,sid),offers=offers(c,sid))
 @app.post('/api/storefront/photo')
 def sf_upload():
  sid=merchant()
  p=payload();value=p.get('image')
  if not isinstance(value,str) or len(value)>350000:return err('Photo trop volumineuse',413)
  try:
   data=base64.b64decode(value,validate=True)
   with Image.open(io.BytesIO(data)) as im:
    if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>16000000:raise ValueError()
    im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1000,1000))
    if p.get('crop') is True:im=ImageOps.fit(im,(min(im.size),min(im.size)))
    b=io.BytesIO();im.save(b,'JPEG',quality=82,optimize=True)
    if b.tell()>180000:
     im.thumbnail((720,720));b=io.BytesIO();im.save(b,'JPEG',quality=72,optimize=True)
    if b.tell()>180000:raise ValueError()
    raw=b.getvalue()
  except (ValueError,OSError,TypeError,binascii.Error,Image.DecompressionBombError):return err('Photo JPEG, PNG ou WebP valide requise')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');merchant(c)
   if c.execute('SELECT COUNT(*) FROM storefront_photos WHERE shop_id=?',(sid,)).fetchone()[0]>=30:return err('Limite de 30 photos atteinte. Supprimez une ancienne photo non utilisée.',409)
   ident=secrets.token_hex(16);c.execute('INSERT INTO storefront_photos VALUES(?,?,?)',(ident,sid,raw))
  return jsonify(id=ident),201
 @app.get('/api/storefront/photos')
 def sf_photos():
  sid=merchant()
  with db() as c:return jsonify(photos=[r[0] for r in c.execute('SELECT id FROM storefront_photos WHERE shop_id=?',(sid,))])
 @app.post('/api/storefront/photo/delete')
 def sf_photo_delete():
  sid=merchant();ident=payload().get('id')
  if not isinstance(ident,str):return err('Photo invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');merchant(c)
   if not photo_owned(c,sid,ident):return err('Photo introuvable',404)
   if c.execute('SELECT 1 FROM storefront_profiles WHERE cover=? UNION SELECT 1 FROM storefront_offers WHERE photo=? UNION SELECT 1 FROM storefront_gallery WHERE photo_id=?',(ident,ident,ident)).fetchone():return err('Photo utilisée : retirez-la d’abord de la vitrine ou de l’offre',409)
   c.execute('DELETE FROM storefront_photos WHERE id=? AND shop_id=?',(ident,sid))
  return jsonify(ok=True)
 @app.get('/media/store/<ident>')
 def sf_media(ident):
  if not re.fullmatch('[a-f0-9]{32}',ident):return err('Photo introuvable',404)
  with db() as c:
   r=c.execute('SELECT p.image FROM storefront_photos p JOIN subscriptions t ON t.shop_id=p.shop_id WHERE p.id=? AND '+ACTIVE+' AND NOT EXISTS(SELECT 1 FROM storefront_hidden_photos h WHERE h.photo_id=p.id) AND (EXISTS(SELECT 1 FROM storefront_profiles f WHERE f.cover=p.id) OR EXISTS(SELECT 1 FROM storefront_gallery g WHERE g.photo_id=p.id AND g.shop_id=p.shop_id) OR EXISTS(SELECT 1 FROM storefront_offers o WHERE o.photo=p.id AND o.active=1 AND o.starts<='+TODAY+' AND o.ends>='+TODAY+'))',(ident,)).fetchone()
   if not r:return err('Photo introuvable',404)
   response=send_file(io.BytesIO(r[0]),mimetype='image/jpeg',max_age=0);response.headers['Cache-Control']='no-store';return response
 @app.post('/api/storefront/profile')
 def sf_save_profile():
  sid=merchant();p=payload();cover=p.get('cover');desc=clean(p.get('description'),1000)
  hours=p.get('hours');gallery=p.get('gallery')
  if hours is not None and (not isinstance(hours,str) or len(hours)>700):return err('Horaires invalides (700 caractères maximum)')
  if gallery is not None and (not isinstance(gallery,list) or len(gallery)>12 or any(not isinstance(v,str) for v in gallery) or len(set(gallery))!=len(gallery)):return err('Galerie invalide (12 photos maximum)')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');merchant(c)
   if not photo_owned(c,sid,cover) or (gallery is not None and any(not photo_owned(c,sid,g) for g in gallery)):return err('Photo invalide')
   current=c.execute('SELECT hours FROM storefront_profiles WHERE shop_id=?',(sid,)).fetchone()
   saved_hours=hours.strip() if hours is not None else (current[0] if current else '')
   c.execute('INSERT INTO storefront_profiles(shop_id,description,cover,hours) VALUES(?,?,?,?) ON CONFLICT(shop_id) DO UPDATE SET description=excluded.description,cover=excluded.cover,hours=excluded.hours',(sid,desc,cover,saved_hours))
   if gallery is not None:
    c.execute('DELETE FROM storefront_gallery WHERE shop_id=?',(sid,))
    c.executemany('INSERT INTO storefront_gallery VALUES(?,?,?)',[(sid,g,i) for i,g in enumerate(gallery)])
  return jsonify(ok=True)
 @app.post('/api/storefront/offer')
 def sf_save_offer():
  sid=merchant();p=payload();kind=p.get('kind');title=clean(p.get('title'),100);desc=clean(p.get('description'),1000);start=p.get('starts');end=p.get('ends');photo=p.get('photo');old=p.get('old_price');new=p.get('new_price');disc=p.get('discount')
  if kind not in ('promotion','pack','coupon') or not title or not desc:return err('Type, titre et conditions requis')
  try:
   if not isinstance(start,str) or not isinstance(end,str) or date.fromisoformat(start).isoformat()!=start or date.fromisoformat(end).isoformat()!=end or start>end or (date.fromisoformat(end)-date.fromisoformat(start)).days>366:raise ValueError()
  except (ValueError,TypeError):return err('Dates invalides (maximum 366 jours)')
  if kind=='coupon':
   if type(disc)is not int or not 1<=disc<=100:return err('Réduction entre 1 et 100 % requise')
   old=new=None
  else:
   if type(old)is not int or type(new)is not int or not 0<=new<old<=10000000:return err('Prix promotionnel inférieur au prix initial requis (millimes)')
   disc=None
  with db() as c:
   c.execute('BEGIN IMMEDIATE');merchant(c)
   if not photo_owned(c,sid,photo):return err('Photo invalide')
   ident=p.get('id')
   values=(kind,title,desc,start,end,old,new,disc,photo)
   if ident is not None:
    if type(ident)is not int:return err('Offre invalide')
    previous=c.execute('SELECT * FROM storefront_offers WHERE id=? AND shop_id=?',(ident,sid)).fetchone()
    if not previous:return err('Offre introuvable',404)
    if not previous['active']:return err('Offre arrêtée : créez une nouvelle offre',409)
    if c.execute('SELECT 1 FROM storefront_coupons WHERE offer_id=?',(ident,)).fetchone():return err('Coupon déjà obtenu : ses conditions ne peuvent plus être modifiées',409)
    c.execute('UPDATE storefront_offers SET kind=?,title=?,description=?,starts=?,ends=?,old_price=?,new_price=?,discount=?,photo=? WHERE id=? AND shop_id=?',(*values,ident,sid))
   else:
    if c.execute('SELECT COUNT(*) FROM storefront_offers WHERE shop_id=?',(sid,)).fetchone()[0]>=200:return err('Limite de 200 offres atteinte',409)
    ident=c.execute('INSERT INTO storefront_offers(shop_id,kind,title,description,starts,ends,old_price,new_price,discount,photo) VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,*values)).lastrowid
  return jsonify(id=ident),200 if p.get('id') is not None else 201
 @app.post('/api/storefront/stop')
 def sf_stop():
  sid=merchant();ident=payload().get('id')
  if type(ident)is not int:return err('Offre invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');merchant(c)
   if not c.execute('UPDATE storefront_offers SET active=0,photo=NULL WHERE id=? AND shop_id=?',(ident,sid)).rowcount:return err('Offre introuvable',404)
  return jsonify(ok=True)
 @app.post('/api/storefront/coupon/claim')
 def sf_claim():
  ident=payload().get('id')
  if type(ident)is not int:return err('Coupon invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');a=account(c)
   if not a:return err('Connectez votre portefeuille',401)
   o=c.execute("SELECT o.id FROM storefront_offers o JOIN subscriptions t ON t.shop_id=o.shop_id WHERE o.id=? AND o.kind='coupon' AND o.active=1 AND o.starts<="+TODAY+" AND o.ends>="+TODAY+" AND "+ACTIVE,(ident,)).fetchone()
   if not o:return err('Coupon indisponible',404)
   r=c.execute('SELECT code,used FROM storefront_coupons WHERE offer_id=? AND account_id=?',(ident,a[0])).fetchone()
   if r:return jsonify(**dict(r),duplicate=True)
   code='TN-'+secrets.token_hex(6).upper();c.execute('INSERT INTO storefront_coupons(code,offer_id,account_id) VALUES(?,?,?)',(code,ident,a[0]))
  return jsonify(code=code,used=None),201
 @app.post('/api/storefront/coupon/redeem')
 def sf_redeem():
  sid=merchant();code=payload().get('code')
  if not isinstance(code,str) or not re.fullmatch('TN-[A-F0-9]{12}',code):return err('Code invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE');merchant(c)
   if not active_shop(c,sid):return err('Commerce indisponible',403)
   r=c.execute("SELECT q.used,o.title,o.discount FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE q.code=? AND o.shop_id=? AND o.active=1 AND o.starts<="+TODAY+" AND o.ends>="+TODAY,(code,sid)).fetchone()
   if not r:return err('Coupon inconnu ou expiré',404)
   if r['used'] is not None:return err('Coupon déjà utilisé',409)
   c.execute('UPDATE storefront_coupons SET used=? WHERE code=?',(int(time.time()),code))
  return jsonify(ok=True,title=r['title'],discount=r['discount'])