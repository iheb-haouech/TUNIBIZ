"""Pilot request hardening. Never log request contents, cookies or identities."""
import hashlib, sqlite3
from flask import request, jsonify, session
from werkzeug.exceptions import HTTPException

def install(app, db, err, throttle):
 with db() as c:
  c.executescript("""
  CREATE INDEX IF NOT EXISTS ledger_customer ON loyalty_ledger(customer_id,id);
  CREATE INDEX IF NOT EXISTS crm_shop ON crm_customers(shop_id,id);
  CREATE INDEX IF NOT EXISTS wallet_account ON wallet_cards(account_id);
  CREATE INDEX IF NOT EXISTS wallet_session_expiry ON wallet_sessions(expires);
  CREATE INDEX IF NOT EXISTS merchant_session_user ON merchant_sessions(user_id,expires);
  CREATE INDEX IF NOT EXISTS offers_shop_dates ON storefront_offers(shop_id,active,starts,ends);
  CREATE INDEX IF NOT EXISTS nearby_shop_dates ON nearby_offers(shop_id,active,starts,ends);
  CREATE INDEX IF NOT EXISTS payments_shop ON cash_payments(shop_id,created);
  """)
 @app.before_request
 def pilot_guard():
  # Protect future PATCH/DELETE routes too; current POST guard remains compatible.
  if request.method in ('PUT','PATCH','DELETE'):
   import secrets
   expected=session.get('csrf')
   if not expected or not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),expected):
    return err('Session invalide, rechargez la page',403)
  # Bound public writes and QR/coupon abuse; no persistent consumer position is used.
  limited={'/api/wallet/store-scan':60,'/api/storefront/coupon/claim':40,
           '/api/loyalty/qr':60,'/api/menu/':30,'/api/analytics/event':120}
  path=request.path
  for prefix,n in limited.items():
   if request.method=='POST' and (path==prefix or (prefix.endswith('/') and path.startswith(prefix))):
    key=hashlib.sha256((request.remote_addr or 'local').encode()).hexdigest()
    if not throttle('pilot:'+prefix,key,n):return err('Trop de demandes. Réessayez plus tard.',429)
    break
 @app.errorhandler(HTTPException)
 def http_error(e):
  messages={400:'Requête invalide',403:'Accès refusé',404:'Introuvable',
            405:'Méthode non autorisée',413:'Fichier ou requête trop volumineux',
            429:'Trop de demandes',500:'Erreur serveur',503:'Service temporairement indisponible'}
  return err(messages.get(e.code,'Requête refusée'),e.code)
 @app.errorhandler(sqlite3.OperationalError)
 def database_error(e):
  # Do not print SQL, database paths or input values in error logs.
  app.logger.warning('Database operation unavailable')
  response= jsonify(error='Service temporairement occupé. Réessayez.')
  response.status_code=503
  response.headers['Retry-After']='3'
  return response
 @app.errorhandler(500)
 def internal_error(e):
  return err('Erreur serveur. Réessayez dans quelques instants.',500)
 @app.after_request
 def pilot_headers(response):
  response.headers['Permissions-Policy']='camera=(self), geolocation=(self), microphone=()'
  if request.path.startswith('/api/'):
   response.headers['Cache-Control']='no-store'
  return response
