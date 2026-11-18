"""Local demo lead intake. Contact permission is specific to the requested demo."""
import re
from flask import jsonify
def install(app,db,payload,clean,merchant,err):
 with db() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS demo_leads(id INTEGER PRIMARY KEY, business TEXT NOT NULL, contact TEXT NOT NULL, phone TEXT NOT NULL, city TEXT NOT NULL, sector TEXT NOT NULL, permission INTEGER NOT NULL CHECK(permission=1), created TEXT DEFAULT CURRENT_TIMESTAMP)""")
 @app.post('/api/demo-request')
 def demo_request():
  p=payload();b=clean(p.get('business'));n=clean(p.get('contact'));phone=clean(p.get('phone'),25);city=clean(p.get('city'),80);sector=clean(p.get('sector'),40)
  if not all([b,n,city,sector]) or not re.fullmatch(r'[+0-9 ()-]{8,25}',phone) or p.get('permission') is not True:return err('Informations et autorisation requises')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if c.execute("SELECT id FROM demo_leads WHERE phone=? AND business=? AND created>=datetime('now','-1 day')",(phone,b)).fetchone():return jsonify(ok=True)
   c.execute('INSERT INTO demo_leads(business,contact,phone,city,sector,permission) VALUES(?,?,?,?,?,1)',(b,n,phone,city,sector))
  return jsonify(ok=True),201
