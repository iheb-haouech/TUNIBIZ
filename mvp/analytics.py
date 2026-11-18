"""Consent-based anonymous aggregate usage; business records remain independent."""
import os,re,time,hashlib
from flask import request,session,jsonify
# Never record request bodies, IPs, tokens, coordinates, account IDs or arbitrary paths.
EVENTS={
 ('GET','/api/crm'):'business_dashboard',('POST','/api/login'):'merchant_login',('POST','/api/logout'):'merchant_logout',
 ('POST','/api/merchant/register'):'merchant_registration',('POST','/api/crm/customer'):'customer_created',
 ('POST','/api/crm/customer/reset'):'card_reset',('POST','/api/crm/customer/consent'):'marketing_preference',
 ('POST','/api/crm/purchase'):'loyalty_purchase',('POST','/api/crm/redeem'):'reward_redeemed',
 ('POST','/api/crm/reward'):'reward_created',('POST','/api/crm/campaign'):'campaign_created',('POST','/api/crm/campaign/stop'):'campaign_stopped',
 ('GET','/api/wallet'):'wallet_view',('POST','/api/wallet/register'):'consumer_registration',('POST','/api/wallet/login'):'consumer_login',
 ('POST','/api/google/login'):'google_login',('POST','/api/wallet/link'):'card_linked',('POST','/api/wallet/select'):'card_selected',
 ('POST','/api/wallet/unlink'):'card_unlinked',('POST','/api/wallet/delete'):'account_deleted',('POST','/api/wallet/logout'):'consumer_logout',
 ('POST','/api/loyalty/login'):'card_login',('GET','/api/loyalty'):'loyalty_view',('POST','/api/loyalty/optout'):'marketing_optout',
 ('POST','/api/loyalty/qr'):'qr_generated',('POST','/api/crm/qr/resolve'):'qr_identified',
 ('GET','/api/nearby'):'nearby_catalog',('GET','/api/nearby/business'):'nearby_business',('POST','/api/nearby/location'):'shop_location_saved',
 ('POST','/api/nearby/offer'):'nearby_offer_created',('POST','/api/nearby/stop'):'nearby_offer_stopped',
 ('POST','/api/demo-request'):'demo_request',('GET','/api/business'):'legacy_business',('POST','/api/business/item'):'item_saved',('POST','/api/business/status'):'order_status'
}
UI={'home_view','wallet_open','business_open','nearby_open','nearby_discovery','nearby_offer_view','nearby_map_enabled','nearby_alert_enabled','merchant_registration_view','privacy_view','loyalty_open'}
def install(app,db,payload,err):
 with db() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS analytics_daily(day TEXT NOT NULL,platform TEXT NOT NULL,event TEXT NOT NULL,n INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(day,platform,event))""")
 def increment(platform,event):
  with db() as c:
   c.execute("INSERT INTO analytics_daily VALUES(date('now','+1 hour'),?,?,1) ON CONFLICT(day,platform,event) DO UPDATE SET n=n+1",(platform,event))
   c.execute("DELETE FROM analytics_daily WHERE day<date('now','-365 days')")
 @app.get('/api/analytics/config')
 def analytics_config():
  mid=os.getenv('TUNIBIZ_GA4_MEASUREMENT_ID','')
  return jsonify(measurement_id=mid if re.fullmatch(r'G-[A-Z0-9]+',mid) else '')
 @app.post('/api/analytics/event')
 def analytics_event():
  p=payload();platform=request.headers.get('X-Tunibiz-Platform')
  if request.headers.get('X-Tunibiz-Analytics')!='yes' or platform not in ('web','android'):return err('Consentement requis',403)
  if set(p)!={'event'} or not isinstance(p['event'],str) or p['event'] not in UI:return err('Evenement invalide')
  increment(platform,p['event']);return jsonify(ok=True)
 @app.after_request
 def analytics_record(response):
  platform=request.headers.get('X-Tunibiz-Platform');event=EVENTS.get((request.method,request.path))
  if response.status_code<300 and response.status_code>=200 and event and platform in ('web','android') and request.headers.get('X-Tunibiz-Analytics')=='yes':
   try:
    increment(platform,event);response.headers['X-Tunibiz-Event']=event
   except Exception:app.logger.warning('Analytics aggregate unavailable')
  return response
 @app.get('/api/admin/overview')
 def admin_overview():
  token=session.get('admin_token')
  with db() as c:
   if not isinstance(token,str) or not c.execute('SELECT 1 FROM admin_sessions WHERE digest=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone():return err('Administration requise',401)
   business=dict(c.execute("""SELECT (SELECT COUNT(*) FROM consumer_accounts) consumers,(SELECT COUNT(*) FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash) cards,(SELECT COUNT(*) FROM shops) shops,(SELECT COUNT(*) FROM subscriptions WHERE status='active' AND paid_until>date('now','+1 hour')) active_shops,(SELECT COALESCE(SUM(amount),0) FROM cash_payments) cash_millimes,(SELECT COUNT(*) FROM loyalty_ledger WHERE kind='purchase') loyalty_purchases,(SELECT COUNT(*) FROM wallet_sessions WHERE expires>?) wallet_sessions""",(int(time.time()),)).fetchone())
   events=[dict(r) for r in c.execute("SELECT platform,event,SUM(n) count FROM analytics_daily WHERE day>=date('now','+1 hour','-29 days') GROUP BY platform,event ORDER BY count DESC")]
   daily=[dict(r) for r in c.execute("SELECT day,platform,SUM(n) count FROM analytics_daily WHERE day>=date('now','+1 hour','-29 days') GROUP BY day,platform ORDER BY day")]
  return jsonify(business=business,events=events,daily=daily,period_days=30)
 @app.get('/api/admin/consumers')
 def admin_consumers():
  token=session.get('admin_token')
  with db() as c:
   if not isinstance(token,str) or not c.execute('SELECT 1 FROM admin_sessions WHERE digest=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone():return err('Administration requise',401)
   offset=request.args.get('offset',0,type=int)
   if offset<0 or offset>1000000:return err('Page invalide')
   rows=[dict(r) for r in c.execute('SELECT a.id,a.name,a.email,a.created,COUNT(w.customer_id) cards FROM consumer_accounts a LEFT JOIN wallet_cards w ON w.account_id=a.id GROUP BY a.id ORDER BY a.id DESC LIMIT 50 OFFSET ?',(offset,))]
  return jsonify(accounts=rows,offset=offset)
