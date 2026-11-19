"""Merchant analytics from recorded loyalty transactions, scoped to authenticated shop."""
from datetime import datetime,timedelta,timezone

def dashboard(c,sid):
 today=datetime.now(timezone(timedelta(hours=1))).date()
 start=today-timedelta(days=29)
 daily={str(start+timedelta(days=i)):{'day':str(start+timedelta(days=i)),'amount':0,'purchases':0,'amount_purchases':0,'redeemed':0,'issued':0} for i in range(30)}
 for r in c.execute("""SELECT date(l.created,'+1 hour') day,
 COALESCE(SUM(CASE WHEN l.kind IN ('purchase','scan') THEN l.amount ELSE 0 END),0) amount,
 COUNT(CASE WHEN l.kind IN ('purchase','scan') THEN 1 END) purchases,
 COUNT(CASE WHEN l.kind='purchase' THEN 1 END) amount_purchases,
 COUNT(CASE WHEN l.kind='redeem' THEN 1 END) redeemed,
 COALESCE(SUM(CASE WHEN l.kind IN ('purchase','scan') THEN l.points ELSE 0 END),0) issued
 FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id
 WHERE a.shop_id=? AND date(l.created,'+1 hour') BETWEEN ? AND ? GROUP BY day""",(sid,str(start),str(today))):
  daily[r['day']]=dict(r)
 buyers=c.execute("""SELECT COUNT(*) buyers,COALESCE(SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END),0) repeat
 FROM (SELECT COUNT(*) n FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id
 WHERE a.shop_id=? AND l.kind IN ('purchase','scan') GROUP BY a.id)""",(sid,)).fetchone()
 shop=c.execute("SELECT s.name,s.city,COALESCE(t.category,'general') category,COALESCE(t.category_detail,'') category_detail FROM shops s LEFT JOIN subscriptions t ON t.shop_id=s.id WHERE s.id=?",(sid,)).fetchone()
 args=(sid,str(today),str(today))
 active=c.execute('SELECT COUNT(*) FROM campaigns WHERE shop_id=? AND active=1 AND starts<=? AND ends>=?',args).fetchone()[0]
 nearby=c.execute('SELECT COUNT(*) FROM nearby_offers WHERE shop_id=? AND active=1 AND starts<=? AND ends>=?',args).fetchone()[0]
 subscription=c.execute('SELECT status,paid_until FROM subscriptions WHERE shop_id=?',(sid,)).fetchone()
 pilot=dict(c.execute("""SELECT
 (SELECT COUNT(*) FROM crm_customers WHERE shop_id=? AND date(created,'+1 hour')>=?) new_customers,
 (SELECT COUNT(DISTINCT a.id) FROM crm_customers a JOIN loyalty_ledger l ON l.customer_id=a.id WHERE a.shop_id=? AND l.kind IN ('purchase','scan') AND date(l.created,'+1 hour')>=?) active_customers,
 (SELECT COALESCE(SUM(l.points),0) FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id WHERE a.shop_id=? AND l.points>0) points_issued,
 (SELECT COUNT(*) FROM store_scan_requests WHERE shop_id=? AND state='pending' AND expires>strftime('%s','now')) pending_qr,
 (SELECT COUNT(*) FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE o.shop_id=?) coupons_claimed,
 (SELECT COUNT(*) FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE o.shop_id=? AND q.used IS NOT NULL) coupons_used,
 (SELECT COUNT(*) FROM storefront_offers WHERE shop_id=? AND active=1 AND starts<=? AND ends>=?) active_offers
 """,(sid,str(start),sid,str(start),sid,sid,sid,sid,sid,str(today),str(today))).fetchone())
 return {'subscription':dict(subscription) if subscription else None,'pilot':pilot,'shop':dict(shop),'daily':list(daily.values()),'buyers':buyers['buyers'],'repeat_buyers':buyers['repeat'],'active_campaigns':active,'active_nearby':nearby,'period_timezone':'Africa/Tunis'}
