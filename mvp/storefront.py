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
  """)
 def account(c):
  t=session.get('wallet_token')
  return c.execute('SELECT account_id FROM wallet_sessions WHERE digest=? AND expires>?',(hashlib.sha256(t.encode()).hexdigest(),int(time.time()))).fetchone() if isinstance(t,str) else None
 def photo_owned(c,sid,p):
  return p is None or (isinstance(p,str) and c.execute('SELECT 1 FROM storefront_photos WHERE id=? AND shop_id=?',(p,sid)).fetchone())
 def profile(c,sid):
  return dict(c.execute("""SELECT s.id,s.slug,s.name,s.city,t.category,t.category_detail,COALESCE(p.description,'') description,p.cover FROM shops s JOIN subscriptions t ON t.shop_id=s.id LEFT JOIN storefront_profiles p ON p.shop_id=s.id WHERE s.id=?""",(sid,)).fetchone())
 def offers(c,sid,public=False):
  extra=" AND active=1 AND starts<="+TODAY+" AND ends>="+TODAY if public else ""
  return [dict(r) for r in c.execute("SELECT id,kind,title,description,starts,ends,old_price,new_price,discount,photo,active FROM storefront_offers WHERE shop_id=?"+extra+" ORDER BY id DESC",(sid,))]
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
   return jsonify(stores=[{**r,'joined':r['id'] in joined} for r in rows])
 @app.get('/api/stores/<int:sid>')
 def sf_store(sid):
  with db() as c:
   if not active_shop(c,sid):return err('Commerce indisponible',404)
   a=account(c);p=profile(c,sid);p['offers']=offers(c,sid,True)
   p['nearby']=[dict(r) for r in c.execute("SELECT id,title,description,starts,ends,category FROM nearby_offers WHERE shop_id=? AND active=1 AND starts<="+TODAY+" AND ends>="+TODAY,(sid,))]
   p['coupons']=[dict(r) for r in c.execute("SELECT q.offer_id,q.code,q.used FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE q.account_id=? AND o.shop_id=? AND o.active=1 AND o.starts<="+TODAY+" AND o.ends>="+TODAY,(a[0],sid))] if a else []
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
    b=io.BytesIO();im.save(b,'JPEG',quality=82,optimize=True)
    if b.tell()>180000:
     im.thumbnail((720,720));b=io.BytesIO();im.save(b,'JPEG',quality=72,optimize=True)
    if b.tell()>180000:raise ValueError()
    raw=b.getvalue()
  except (ValueError,OSError,TypeError,binascii.Error,Image.DecompressionBombError):return err('Photo JPEG, PNG ou WebP valide requise')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
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
   c.execute('BEGIN IMMEDIATE')
   if not photo_owned(c,sid,ident):return err('Photo introuvable',404)
   if c.execute('SELECT 1 FROM storefront_profiles WHERE cover=? UNION SELECT 1 FROM storefront_offers WHERE photo=?',(ident,ident)).fetchone():return err('Photo utilisée : retirez-la d’abord de la vitrine ou de l’offre',409)
   c.execute('DELETE FROM storefront_photos WHERE id=? AND shop_id=?',(ident,sid))
  return jsonify(ok=True)
 @app.get('/media/store/<ident>')
 def sf_media(ident):
  if not re.fullmatch('[a-f0-9]{32}',ident):return err('Photo introuvable',404)
  with db() as c:
   r=c.execute('SELECT p.image FROM storefront_photos p JOIN subscriptions t ON t.shop_id=p.shop_id WHERE p.id=? AND '+ACTIVE+' AND (EXISTS(SELECT 1 FROM storefront_profiles f WHERE f.cover=p.id) OR EXISTS(SELECT 1 FROM storefront_offers o WHERE o.photo=p.id AND o.active=1 AND o.starts<='+TODAY+' AND o.ends>='+TODAY+'))',(ident,)).fetchone()
   if not r:return err('Photo introuvable',404)
   response=send_file(io.BytesIO(r[0]),mimetype='image/jpeg',max_age=0);response.headers['Cache-Control']='no-store';return response
 @app.post('/api/storefront/profile')
 def sf_save_profile():
  sid=merchant();p=payload();cover=p.get('cover');desc=clean(p.get('description'),1000)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not photo_owned(c,sid,cover):return err('Photo invalide')
   c.execute('INSERT INTO storefront_profiles VALUES(?,?,?) ON CONFLICT(shop_id) DO UPDATE SET description=excluded.description,cover=excluded.cover',(sid,desc,cover))
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
   c.execute('BEGIN IMMEDIATE')
   if not photo_owned(c,sid,photo):return err('Photo invalide')
   if c.execute('SELECT COUNT(*) FROM storefront_offers WHERE shop_id=?',(sid,)).fetchone()[0]>=200:return err('Limite de 200 offres atteinte',409)
   ident=c.execute('INSERT INTO storefront_offers(shop_id,kind,title,description,starts,ends,old_price,new_price,discount,photo) VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,kind,title,desc,start,end,old,new,disc,photo)).lastrowid
  return jsonify(id=ident),201
 @app.post('/api/storefront/stop')
 def sf_stop():
  sid=merchant();ident=payload().get('id')
  if type(ident)is not int:return err('Offre invalide')
  with db() as c:
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
   if r:return jsonify(dict(r))
   code='TN-'+secrets.token_hex(6).upper();c.execute('INSERT INTO storefront_coupons(code,offer_id,account_id) VALUES(?,?,?)',(code,ident,a[0]))
  return jsonify(code=code,used=None),201
 @app.post('/api/storefront/coupon/redeem')
 def sf_redeem():
  sid=merchant();code=payload().get('code')
  if not isinstance(code,str) or not re.fullmatch('TN-[A-F0-9]{12}',code):return err('Code invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if not active_shop(c,sid):return err('Commerce indisponible',403)
   r=c.execute("SELECT q.used,o.title,o.discount FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE q.code=? AND o.shop_id=? AND o.active=1 AND o.starts<="+TODAY+" AND o.ends>="+TODAY,(code,sid)).fetchone()
   if not r:return err('Coupon inconnu ou expiré',404)
   if r['used'] is not None:return err('Coupon déjà utilisé',409)
   c.execute('UPDATE storefront_coupons SET used=? WHERE code=?',(int(time.time()),code))
  return jsonify(ok=True,title=r['title'],discount=r['discount'])
