"""Optional mobile APIs for the existing schema. Installing routes performs no SQL.
No schema migration, QR replacement or website change. Production deployment is separate.
"""
import hashlib
import os
import re
import time
from flask import jsonify, request, session

CATEGORIES={'grocery_general','drugstore','grocery','coffee','restaurant','bakery','shopping','clothing','other','general','drinks','beauty'}
STATES={'pending','approved','rejected','expired'}

def install(app, db, payload, merchant, err):
    if 'mobile_capabilities_v060' in app.view_functions:
        return
    @app.get('/api/mobile/capabilities')
    def mobile_capabilities_v060():
        response=jsonify(version=1, features={'scan_history':True,'business_category':True,'public_partners':True})
        response.headers['Cache-Control']='no-store'
        return response

    @app.get('/api/mobile/business/scans')
    def mobile_scan_history_v060():
        sid=merchant()
        status=request.args.get('state','')
        try:limit=int(request.args.get('limit','30'))
        except ValueError:return err('Page invalide',400)
        if not 1<=limit<=100 or status and status not in STATES:return err('Filtre invalide',400)
        where=['r.shop_id=?'];params=[sid]
        effective="CASE WHEN r.state='pending' AND r.expires<=? THEN 'expired' ELSE r.state END"
        now=int(time.time())
        if status:where.append('('+effective+')=?');params.extend([now,status])
        cursor=request.args.get('cursor','')
        if cursor:
            match=re.fullmatch(r'(\d{1,12}):([A-Za-z0-9_-]{1,80})',cursor)
            if not match:return err('Page invalide',400)
            before=int(match[1]);where.append('(r.created<? OR (r.created=? AND r.id<?))');params.extend([before,before,match[2]])
        sql='SELECT r.id,a.name,r.created,r.expires,r.decided,r.points,'+effective+' state FROM store_scan_requests r JOIN crm_customers a ON a.id=r.customer_id AND a.shop_id=r.shop_id WHERE '+' AND '.join(where)+' ORDER BY r.created DESC,r.id DESC LIMIT ?'
        with db() as c:rows=[dict(r) for r in c.execute(sql,[now,*params,limit+1])]
        more=len(rows)>limit;rows=rows[:limit]
        response=jsonify(requests=rows,next_cursor=(str(rows[-1]['created'])+':'+rows[-1]['id']) if more else None)
        response.headers['Cache-Control']='no-store'
        return response

    @app.post('/api/mobile/business/category')
    def mobile_business_category_v060():
        sid=merchant();p=payload()
        if set(p)-{'category','category_detail'}:return err('Informations invalides',400)
        category=p.get('category');detail=p.get('category_detail','')
        if not isinstance(category,str) or category not in CATEGORIES or not isinstance(detail,str) or len(detail)>80 or any(ord(x)<32 for x in detail):return err('Catégorie invalide',400)
        detail=detail.strip() if category=='other' else ''
        if category=='other' and not detail:return err('Précisez le type d’établissement',400)
        raw=session.get('merchant_token')
        if not isinstance(raw,str):return err('Connexion requise',401)
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            allowed=c.execute("SELECT 1 FROM merchant_sessions m JOIN users u ON u.id=m.user_id JOIN subscriptions t ON t.shop_id=u.shop_id WHERE m.digest=? AND m.expires>? AND u.shop_id=? AND t.status='active' AND t.paid_until>date('now','+1 hour')",(hashlib.sha256(raw.encode()).hexdigest(),int(time.time()),sid)).fetchone()
            if not allowed:return err('Connexion requise',401)
            c.execute('UPDATE subscriptions SET category=?,category_detail=? WHERE shop_id=?',(category,detail,sid))
            c.execute("INSERT INTO commerce_audit(shop_id,action) VALUES(?,'storefront_category_saved')",(sid,))
        return jsonify(ok=True,category=category,category_detail=detail)

    @app.get('/api/mobile/partners')
    def mobile_public_partners_v060():
        # Listing a private/incomplete partner requires explicit operator authorization.
        approved=[v.strip() for v in os.getenv('TUNIBIZ_PUBLIC_PARTNER_SLUGS','').split(',') if re.fullmatch(r'[A-Za-z0-9_-]{1,80}',v.strip())][:200]
        permitted='COALESCE(p.published,0)=1';params=[]
        if approved:permitted+=' OR s.slug IN ('+','.join('?' for _ in approved)+')';params.extend(approved)
        with db() as c:
            rows=[dict(r) for r in c.execute("SELECT s.id,s.slug,s.name,s.city,t.category,t.category_detail,COALESCE(p.social,'') social FROM shops s JOIN subscriptions t ON t.shop_id=s.id LEFT JOIN storefront_profiles p ON p.shop_id=s.id WHERE t.status='active' AND t.paid_until>date('now','+1 hour') AND ("+permitted+') ORDER BY s.name,s.id LIMIT 500',params)]
        response=jsonify(stores=rows);response.headers['Cache-Control']='no-store'
        return response
