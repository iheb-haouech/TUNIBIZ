"""Merchant analytics from recorded loyalty transactions, scoped to authenticated shop."""
from datetime import datetime,timedelta,timezone

def dashboard(c,sid):
 today=datetime.now(timezone(timedelta(hours=1))).date()
 start=today-timedelta(days=29)
 daily={str(start+timedelta(days=i)):{'day':str(start+timedelta(days=i)),'amount':0,'purchases':0,'redeemed':0,'issued':0} for i in range(30)}
 for r in c.execute("""SELECT date(l.created,'+1 hour') day,
 COALESCE(SUM(CASE WHEN l.kind='purchase' THEN l.amount ELSE 0 END),0) amount,
 COUNT(CASE WHEN l.kind='purchase' THEN 1 END) purchases,
 COUNT(CASE WHEN l.kind='redeem' THEN 1 END) redeemed,
 COALESCE(SUM(CASE WHEN l.kind='purchase' THEN l.points ELSE 0 END),0) issued
 FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id
 WHERE a.shop_id=? AND date(l.created,'+1 hour') BETWEEN ? AND ? GROUP BY day""",(sid,str(start),str(today))):
  daily[r['day']]=dict(r)
 buyers=c.execute("""SELECT COUNT(*) buyers,COALESCE(SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END),0) repeat
 FROM (SELECT COUNT(*) n FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id
 WHERE a.shop_id=? AND l.kind='purchase' GROUP BY a.id)""",(sid,)).fetchone()
 shop=c.execute('SELECT name,city FROM shops WHERE id=?',(sid,)).fetchone()
 args=(sid,str(today),str(today))
 active=c.execute('SELECT COUNT(*) FROM campaigns WHERE shop_id=? AND active=1 AND starts<=? AND ends>=?',args).fetchone()[0]
 nearby=c.execute('SELECT COUNT(*) FROM nearby_offers WHERE shop_id=? AND active=1 AND starts<=? AND ends>=?',args).fetchone()[0]
 return {'shop':dict(shop),'daily':list(daily.values()),'buyers':buyers['buyers'],'repeat_buyers':buyers['repeat'],'active_campaigns':active,'active_nearby':nearby,'period_timezone':'Africa/Tunis'}
