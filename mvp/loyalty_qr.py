"""One-time checkout identification tokens. No account credentials in QR."""
import hashlib,re,secrets,time
from flask import jsonify,session

def install(app,db,payload,merchant,err):
 with db() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS loyalty_scan_tokens (
   digest TEXT PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES crm_customers(id) ON DELETE CASCADE,
   card_hash TEXT NOT NULL, expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0)""")
  c.execute('CREATE INDEX IF NOT EXISTS scan_customer ON loyalty_scan_tokens(customer_id)')
 def digest(t): return hashlib.sha256(t.encode('ascii')).hexdigest()
 @app.post('/api/loyalty/qr')
 def issue_qr():
  import qrcode
  now=int(time.time())
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   a=c.execute('SELECT id,code_hash FROM crm_customers WHERE id=? AND code_hash=?',(session.get('card'),session.get('card_hash'))).fetchone()
   if not a:return err('Connexion requise',401)
   token='TNB1:'+secrets.token_urlsafe(18)
   q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,border=4)
   q.add_data(token);q.make(fit=True)
   c.execute('DELETE FROM loyalty_scan_tokens WHERE expires<=? OR customer_id=?',(now,a['id']))
   c.execute('INSERT INTO loyalty_scan_tokens(digest,customer_id,card_hash,expires) VALUES(?,?,?,?)',(digest(token),a['id'],a['code_hash'],now+90))
  return jsonify(token=token,expires_in=90,matrix=q.get_matrix()),201
 @app.post('/api/crm/qr/resolve')
 def resolve_qr():
  sid=merchant()
  token=payload().get('token')
  if not isinstance(token,str) or not re.fullmatch(r'TNB1:[A-Za-z0-9_-]{24}',token):return err('Code QR invalide')
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   r=c.execute("""SELECT t.digest,a.id,a.name FROM loyalty_scan_tokens t JOIN crm_customers a
    ON a.id=t.customer_id AND a.code_hash=t.card_hash
    WHERE t.digest=? AND t.used=0 AND t.expires>? AND a.shop_id=?""",(digest(token),int(time.time()),sid)).fetchone()
   if not r:return err('Code expiré, utilisé ou non valable pour ce commerce',404)
   c.execute('UPDATE loyalty_scan_tokens SET used=1 WHERE digest=?',(r['digest'],))
   points=c.execute('SELECT COALESCE(SUM(points),0) FROM loyalty_ledger WHERE customer_id=?',(r['id'],)).fetchone()[0]
  return jsonify(customer={'id':r['id'],'name':r['name'],'points':points})
