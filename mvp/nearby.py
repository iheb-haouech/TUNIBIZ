"""Nearby offers: public campaign catalogue; visitor coordinates never sent here."""
from datetime import date
import math
from flask import jsonify, send_from_directory
def install(app,db,payload,clean,merchant,err):
 with db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS nearby_locations(shop_id INTEGER PRIMARY KEY REFERENCES shops(id),lat REAL NOT NULL,lon REAL NOT NULL,address TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS nearby_offers(id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),title TEXT NOT NULL,description TEXT NOT NULL,starts TEXT NOT NULL,ends TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created TEXT DEFAULT CURRENT_TIMESTAMP);
  """)
  cols={r['name'] for r in c.execute('PRAGMA table_info(nearby_offers)')}
  if 'category' not in cols:c.execute("ALTER TABLE nearby_offers ADD COLUMN category TEXT NOT NULL DEFAULT 'general'")
 @app.get('/nearby')
 @app.get('/nearby/business')
 def nearby_page():return send_from_directory(app.static_folder,'nearby.html')
 @app.get('/api/nearby')
 def nearby():
  today=date.today().isoformat()
  with db() as c:
   offers=[dict(r) for r in c.execute("""SELECT o.id,s.name shop,l.lat,l.lon,l.address,o.title,o.description,o.ends,o.category,1000 radius FROM nearby_offers o JOIN nearby_locations l ON o.shop_id=l.shop_id JOIN shops s ON s.id=o.shop_id WHERE o.active=1 AND o.starts<=? AND o.ends>=? ORDER BY o.id DESC""",(today,today))]
  return jsonify(offers=offers)
 @app.get('/api/nearby/business')
 def nearby_business():
  sid=merchant()
  with db() as c:
   loc=c.execute('SELECT lat,lon,address FROM nearby_locations WHERE shop_id=?',(sid,)).fetchone()
   return jsonify(location=dict(loc) if loc else None,offers=[dict(r) for r in c.execute('SELECT id,title,description,starts,ends,active,category FROM nearby_offers WHERE shop_id=? ORDER BY id DESC',(sid,))],radius=1000)
 @app.post('/api/nearby/location')
 def nearby_location():
  sid=merchant();p=payload()
  try:
   lat=float(p['lat']);lon=float(p['lon'])
   if not(math.isfinite(lat) and math.isfinite(lon) and 30<=lat<=38 and 7<=lon<=12):raise ValueError()
  except (KeyError,TypeError,ValueError):return err('Coordonnées du commerce invalides (Tunisie)')
  address=clean(p.get('address'),180)
  if not address:return err('Adresse requise')
  with db() as c:c.execute('INSERT INTO nearby_locations(shop_id,lat,lon,address) VALUES(?,?,?,?) ON CONFLICT(shop_id) DO UPDATE SET lat=excluded.lat,lon=excluded.lon,address=excluded.address',(sid,lat,lon,address))
  return jsonify(ok=True)
 @app.post('/api/nearby/offer')
 def nearby_offer():
  sid=merchant();p=payload();title=clean(p.get('title'),80);description=clean(p.get('description'),500);starts=clean(p.get('starts'),10);ends=clean(p.get('ends'),10);category=p.get('category','general')
  try:
   if date.fromisoformat(ends)<date.fromisoformat(starts):raise ValueError()
  except ValueError:return err('Dates invalides')
  if not title or not description or category not in ('general','coffee','restaurant','bakery','drinks','shopping','beauty'):return err('Titre, conditions et categorie valides requis')
  with db() as c:
   if not c.execute('SELECT 1 FROM nearby_locations WHERE shop_id=?',(sid,)).fetchone():return err('Configurez votre établissement en premier')
   oid=c.execute('INSERT INTO nearby_offers(shop_id,title,description,starts,ends,category) VALUES(?,?,?,?,?,?)',(sid,title,description,starts,ends,category)).lastrowid
  return jsonify(id=oid),201
 @app.post('/api/nearby/stop')
 def nearby_stop():
  sid=merchant();p=payload()
  if type(p.get('id')) is not int:return err('Identifiant invalide')
  with db() as c:
   if not c.execute('UPDATE nearby_offers SET active=0 WHERE shop_id=? AND id=?',(sid,p['id'])).rowcount:return err('Offre introuvable',404)
  return jsonify(ok=True)
