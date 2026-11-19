"""V0.5.2 commerce flows. Additive schema; all balances remain shop scoped.

Phone numbers are contact identifiers, never credentials or proof of ownership.
Until an SMS provider is configured they stay explicitly unverified. Membership
is approved by the signed-in consumer; collisions require a merchant invitation.
"""
import hashlib
import json
import re
import secrets
import time
from datetime import date, timedelta
from flask import abort, jsonify, request, session, send_from_directory
from business_clock import today


def phone_number(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('Numéro de téléphone invalide')
    value = re.sub(r'[\s().-]', '', value)
    if value.startswith('00'):
        value = '+' + value[2:]
    if re.fullmatch(r'[2459]\d{7}', value):
        value = '+216' + value
    if not re.fullmatch(r'\+[1-9]\d{7,14}', value):
        raise ValueError('Utilisez un numéro international, par exemple +216 20 123 456')
    if value.startswith('+216') and not re.fullmatch(r'\+216[2459]\d{7}', value):
        raise ValueError('Numéro tunisien invalide')
    return value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def install(app, db, payload, clean, merchant, err, throttle):
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS commerce_audit(
          id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),
          action TEXT NOT NULL,object_id INTEGER,details TEXT NOT NULL DEFAULT '{}',
          created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS commerce_phones(
          account_id INTEGER PRIMARY KEY REFERENCES consumer_accounts(id) ON DELETE CASCADE,
          phone TEXT NOT NULL,verified INTEGER NOT NULL DEFAULT 0,shared INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS commerce_invites(
          digest TEXT PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),
          customer_id INTEGER NOT NULL REFERENCES crm_customers(id),expires INTEGER NOT NULL,
          used INTEGER,account_id INTEGER REFERENCES consumer_accounts(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS commerce_imports(
          source TEXT NOT NULL,source_id INTEGER NOT NULL,offer_id INTEGER NOT NULL REFERENCES storefront_offers(id),
          PRIMARY KEY(source,source_id));
        CREATE TABLE IF NOT EXISTS commerce_codes(
          id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),digest TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,discount INTEGER NOT NULL,expires TEXT NOT NULL,
          max_uses INTEGER NOT NULL,customer_id INTEGER REFERENCES crm_customers(id),active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS commerce_code_uses(
          code_id INTEGER NOT NULL REFERENCES commerce_codes(id),account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,
          created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(code_id,account_id));
        CREATE TABLE IF NOT EXISTS commerce_sponsors(
          id INTEGER PRIMARY KEY,shop_id INTEGER NOT NULL REFERENCES shops(id),title TEXT NOT NULL,
          description TEXT NOT NULL,photo TEXT REFERENCES storefront_photos(id),starts TEXT NOT NULL,ends TEXT NOT NULL,
          cta TEXT NOT NULL DEFAULT 'Découvrir',priority INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'draft');
        CREATE TABLE IF NOT EXISTS commerce_notifications(
          id INTEGER PRIMARY KEY,account_id INTEGER NOT NULL REFERENCES consumer_accounts(id) ON DELETE CASCADE,
          shop_id INTEGER REFERENCES shops(id),title TEXT NOT NULL,body TEXT NOT NULL,
          kind TEXT NOT NULL,created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,seen INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS commerce_preferences(
          account_id INTEGER PRIMARY KEY REFERENCES consumer_accounts(id) ON DELETE CASCADE,
          marketing INTEGER NOT NULL DEFAULT 0,personalization INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS commerce_notifications_account ON commerce_notifications(account_id,id);
        CREATE INDEX IF NOT EXISTS commerce_audit_shop ON commerce_audit(shop_id,id);
        ''')
        additions = {
            'crm_customers': {'phone_normalized': 'TEXT'},
            'storefront_profiles': {'photo': 'TEXT REFERENCES storefront_photos(id)', 'logo': 'TEXT REFERENCES storefront_photos(id)', 'phone': "TEXT NOT NULL DEFAULT ''", 'website': "TEXT NOT NULL DEFAULT ''", 'social': "TEXT NOT NULL DEFAULT ''", 'published': 'INTEGER NOT NULL DEFAULT 0'},
            'storefront_offers': {'audience': "TEXT NOT NULL DEFAULT 'public'", 'benefit': "TEXT NOT NULL DEFAULT 'discount'", 'conditions': "TEXT NOT NULL DEFAULT ''", 'state': "TEXT NOT NULL DEFAULT 'active'", 'max_uses': 'INTEGER', 'nearby_enabled': 'INTEGER NOT NULL DEFAULT 0', 'radius': 'INTEGER', 'visual': "TEXT NOT NULL DEFAULT 'general'"},
            'rewards': {'conditions': "TEXT NOT NULL DEFAULT ''", 'photo': 'TEXT REFERENCES storefront_photos(id)'},
            'nearby_offers': {'promotion_id': 'INTEGER REFERENCES storefront_offers(id)'},
        }
        for table, fields in additions.items():
            cols = {r['name'] for r in c.execute('PRAGMA table_info('+table+')')}
            for name, definition in fields.items():
                if name not in cols:
                    c.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' '+definition)
        for r in c.execute("SELECT id,phone FROM crm_customers WHERE phone_normalized IS NULL AND phone<>''").fetchall():
            try:
                c.execute('UPDATE crm_customers SET phone_normalized=? WHERE id=?', (phone_number(r['phone']), r['id']))
            except ValueError:
                pass  # Preserve legacy contacts without silently changing their identity.
        c.execute('CREATE INDEX IF NOT EXISTS commerce_customer_phone ON crm_customers(shop_id,phone_normalized)')
        # Idempotently merge old sources, preserving identifiers and coupon references.
        for source in ('campaigns', 'nearby_offers'):
            for r in c.execute('SELECT * FROM '+source).fetchall():
                if c.execute('SELECT 1 FROM commerce_imports WHERE source=? AND source_id=?', (source, r['id'])).fetchone():
                    continue
                public = source == 'nearby_offers'
                oid = c.execute('''INSERT INTO storefront_offers(shop_id,kind,title,description,starts,ends,active,audience,benefit,state,nearby_enabled)
                    VALUES(?,'promotion',?,?,?,?,?,?,'advantage',?,?)''',
                    (r['shop_id'],r['title'],r['description'],r['starts'],r['ends'],r['active'], 'public' if public else ('members' if r['segment']=='all' else r['segment']), 'active' if r['active'] else 'suspended', int(public))).lastrowid
                c.execute('INSERT INTO commerce_imports VALUES(?,?,?)', (source,r['id'],oid))
                if not public:c.execute('UPDATE storefront_offers SET visual=? WHERE id=?',(r['visual'],oid))
                if public:
                    c.execute('UPDATE nearby_offers SET promotion_id=? WHERE id=?', (oid,r['id']))
        c.execute("INSERT OR IGNORE INTO pilot_migrations VALUES('commerce-v052')")
        c.executescript('''
        CREATE TRIGGER IF NOT EXISTS commerce_ledger_notice AFTER INSERT ON loyalty_ledger
        WHEN NEW.kind IN ('manual','redeem','welcome')
        BEGIN
          INSERT INTO commerce_notifications(account_id,shop_id,title,body,kind)
          SELECT w.account_id,a.shop_id,
            CASE WHEN NEW.kind='redeem' THEN 'Avantage utilisé'
                 WHEN NEW.points>0 AND EXISTS(SELECT 1 FROM rewards r WHERE r.shop_id=a.shop_id AND r.active=1
                   AND r.cost<=(SELECT COALESCE(SUM(points),0) FROM loyalty_ledger WHERE customer_id=a.id)
                   AND r.cost>(SELECT COALESCE(SUM(points),0)-NEW.points FROM loyalty_ledger WHERE customer_id=a.id))
                 THEN 'Un nouvel avantage est disponible' ELSE 'Votre fidélité évolue' END,
            'Une nouvelle activité est disponible dans la fidélité de votre commerce.','transactional'
          FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash WHERE a.id=NEW.customer_id;
        END;
        CREATE TRIGGER IF NOT EXISTS commerce_coupon_notice AFTER UPDATE OF used ON storefront_coupons
        WHEN OLD.used IS NULL AND NEW.used IS NOT NULL
        BEGIN
          INSERT INTO commerce_notifications(account_id,shop_id,title,body,kind)
          SELECT NEW.account_id,o.shop_id,'Coupon utilisé','Votre avantage a été validé dans votre commerce.','transactional'
          FROM storefront_offers o WHERE o.id=NEW.offer_id;
        END;
        CREATE TABLE IF NOT EXISTS commerce_push_outbox(
          id INTEGER PRIMARY KEY,device_id TEXT NOT NULL REFERENCES push_devices(device_id) ON DELETE CASCADE,
          notification_id INTEGER NOT NULL REFERENCES commerce_notifications(id) ON DELETE CASCADE,
          created INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,next_attempt INTEGER NOT NULL DEFAULT 0,
          UNIQUE(device_id,notification_id));
        CREATE TRIGGER IF NOT EXISTS commerce_push_notice AFTER INSERT ON commerce_notifications
        BEGIN
          INSERT OR IGNORE INTO commerce_push_outbox(device_id,notification_id,created)
          SELECT d.device_id,NEW.id,CAST(strftime('%s','now') AS INTEGER)
          FROM push_devices d JOIN wallet_sessions s ON s.digest=d.session_digest
          WHERE s.account_id=NEW.account_id AND s.expires>CAST(strftime('%s','now') AS INTEGER);
        END;
        CREATE TRIGGER IF NOT EXISTS commerce_anonymize_contact AFTER UPDATE OF name,phone ON crm_customers
        WHEN NEW.name='Client anonymise' AND NEW.phone=''
        BEGIN
          UPDATE crm_customers SET phone_normalized=NULL WHERE id=NEW.id;
          DELETE FROM commerce_invites WHERE customer_id=NEW.id;
          UPDATE commerce_audit SET details='{}' WHERE shop_id=NEW.shop_id AND object_id=NEW.id
            AND action IN ('customer_created','points_adjusted','membership_approved','invitation_created');
        END;
        ''')

    def account(c):
        token = session.get('wallet_token')
        return c.execute('''SELECT a.id,a.name,a.email,a.email_verified FROM consumer_accounts a JOIN wallet_sessions s ON s.account_id=a.id
            WHERE s.digest=? AND s.expires>?''', (digest(token),int(time.time()))).fetchone() if isinstance(token,str) else None

    def admin(c):
        token = session.get('admin_token')
        if not isinstance(token,str) or not c.execute('SELECT 1 FROM admin_sessions WHERE digest=? AND expires>?',(digest(token),int(time.time()))).fetchone():
            abort(401)

    def audit(c,sid,action,ident=None,**details):
        c.execute('INSERT INTO commerce_audit(shop_id,action,object_id,details) VALUES(?,?,?,?)',(sid,action,ident,json.dumps(details)))

    def notify(c,cid,title,body,kind='transactional'):
        for r in c.execute('SELECT w.account_id,a.shop_id FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash WHERE a.id=?',(cid,)):
            c.execute('INSERT INTO commerce_notifications(account_id,shop_id,title,body,kind) VALUES(?,?,?,?,?)',(r['account_id'],r['shop_id'],title,body,kind))

    def member(c,aid,sid):
        return c.execute('''SELECT a.* FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id AND a.code_hash=w.card_hash
          WHERE w.account_id=? AND a.shop_id=? ORDER BY a.id LIMIT 1''',(aid,sid)).fetchone() if aid else None

    def balance(c,cid):
        return c.execute('SELECT COALESCE(SUM(points),0) FROM loyalty_ledger WHERE customer_id=?',(cid,)).fetchone()[0]

    def owned(c,sid,photo):
        return photo is None or isinstance(photo,str) and bool(c.execute('SELECT 1 FROM storefront_photos WHERE id=? AND shop_id=? AND NOT EXISTS(SELECT 1 FROM storefront_hidden_photos WHERE photo_id=?)',(photo,sid,photo)).fetchone())

    def is_active(c,sid):
        return c.execute("SELECT 1 FROM subscriptions WHERE shop_id=? AND status='active' AND paid_until>date('now','+1 hour')",(sid,)).fetchone()

    def visible(c,o,aid):
        if not o['active'] or o['state']!='active' or not o['starts']<=str(today())<=o['ends']:
            return False
        if o['audience']=='personal':
            return bool(aid and c.execute('SELECT 1 FROM storefront_coupons WHERE account_id=? AND offer_id=?',(aid,o['id'])).fetchone())
        if o['audience']=='public':
            return True
        m=member(c,aid,o['shop_id'])
        if not m or not m['consent']:
            return False
        if o['audience']=='vip':
            return balance(c,m['id'])>=100  # Points, never spending.
        if o['audience']=='inactive':
            last=c.execute('SELECT MAX(created) FROM loyalty_ledger WHERE customer_id=?',(m['id'],)).fetchone()[0]
            return bool(last and last[:10]<str(today()-timedelta(days=30)))
        return True

    def status(o):
        if o['state'] in ('draft','suspended','archived'):
            return o['state']
        if not o['active']:
            return 'suspended'
        return 'expired' if o['ends']<str(today()) else 'scheduled' if o['starts']>str(today()) else 'active'

    def offer_json(o):
        d=dict(o);d.update(status=status(o),old_price=None,new_price=None,reduction_percent=o['discount'] if o['discount']is not None else ((o['old_price']-o['new_price'])*100)//o['old_price'] if o['old_price'] else None)
        return d

    def offers(c,sid=None,aid=None,public=True):
        records=c.execute('SELECT * FROM storefront_offers'+(' WHERE shop_id=?' if sid else '')+' ORDER BY id DESC LIMIT 500',(sid,) if sid else ()).fetchall()
        result=[]
        for r in records:
            if public and (not is_active(c,r['shop_id']) or not visible(c,r,aid)):continue
            item=offer_json(r)
            if public and item['photo'] and not owned(c,r['shop_id'],item['photo']):item['photo']=None
            result.append(item)
        return result

    def profile(c,sid):
        r=c.execute('''SELECT s.*,t.category,t.category_detail,p.description,p.cover,p.photo,p.logo,p.hours,p.phone,p.website,p.social,p.published,l.address,l.lat,l.lon
          FROM shops s JOIN subscriptions t ON t.shop_id=s.id LEFT JOIN storefront_profiles p ON p.shop_id=s.id LEFT JOIN nearby_locations l ON l.shop_id=s.id WHERE s.id=?''',(sid,)).fetchone()
        if not r:return None
        d=dict(r)
        for field in ('photo','cover','logo'):
            if d[field] and not owned(c,sid,d[field]):d[field]=None
        required={'name':d['name'],'category':d['category'],'photo':d['photo'],'city':d['city'],'address':d['address'],'phone':d['phone']}
        d['missing']=[k for k,v in required.items() if not v]
        d['completeness']=round((len(required)-len(d['missing']))*100/len(required))
        d['gallery']=[r[0] for r in c.execute('SELECT g.photo_id FROM storefront_gallery g WHERE g.shop_id=? AND NOT EXISTS(SELECT 1 FROM storefront_hidden_photos h WHERE h.photo_id=g.photo_id) ORDER BY g.position',(sid,))]
        return d

    def directory(c,aid=None):
        result=[]
        for r in c.execute("SELECT shop_id FROM subscriptions WHERE status='active' AND paid_until>date('now','+1 hour')"):
            p=profile(c,r[0])
            if not p or not p['published'] or p['missing']:continue
            p['cover']=p['photo']
            p['joined']=bool(member(c,aid,p['id']))
            p['favorite']=bool(aid and c.execute('SELECT 1 FROM storefront_favorites WHERE account_id=? AND shop_id=?',(aid,p['id'])).fetchone())
            p['offers_count']=len(offers(c,p['id'],aid))
            result.append(p)
        return result

    @app.get('/api/commerce/home')
    def commerce_home():
        with db() as c:
            a=account(c);aid=a['id'] if a else None;stores=directory(c,aid);ids={s['id'] for s in stores}
            pref=c.execute('SELECT marketing,personalization FROM commerce_preferences WHERE account_id=?',(aid,)).fetchone() if aid else None
            banners=[{**dict(r),'sponsored':True,'destination':'/stores?id='+str(r['shop_id'])} for r in c.execute("SELECT * FROM commerce_sponsors WHERE status='active' AND starts<=? AND ends>=? ORDER BY priority DESC,id DESC LIMIT 20",(str(today()),str(today()))) if r['shop_id'] in ids]
            return jsonify(stores=stores,offers=[o for o in offers(c,aid=aid) if o['shop_id'] in ids],sponsors=banners,categories=sorted({s['category'] for s in stores}),profile=dict(a) if a else None,version='0.5.2',preferences=dict(pref) if pref else {'marketing':0,'personalization':0})

    @app.get('/api/commerce/profile')
    def commerce_profile():
        with db() as c:
            a=account(c)
            if not a:return err('Connexion requise',401)
            p=c.execute('SELECT phone,verified,shared FROM commerce_phones WHERE account_id=?',(a['id'],)).fetchone()
            return jsonify(profile=dict(a),phone=dict(p) if p else None,phone_verification_available=False,notifications=[dict(r) for r in c.execute('SELECT id,shop_id,title,body,kind,created,seen FROM commerce_notifications WHERE account_id=? ORDER BY id DESC LIMIT 100',(a['id'],))])

    @app.post('/api/commerce/profile')
    def commerce_profile_save():
        p=payload()
        try:phone=phone_number(p.get('phone'))
        except ValueError as e:return err(str(e))
        if type(p.get('shared')) is not bool or type(p.get('marketing',False)) is not bool or type(p.get('personalization',False)) is not bool:return err('Choix invalide')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');a=account(c)
            if not a:return err('Connexion requise',401)
            previous=c.execute('SELECT phone FROM commerce_phones WHERE account_id=?',(a['id'],)).fetchone()
            if previous and previous[0]!=phone and c.execute('SELECT 1 FROM wallet_cards WHERE account_id=?',(a['id'],)).fetchone():
                return err('Pour modifier le numéro lié à vos cartes, contactez TUNIBIZ.',409)
            c.execute('INSERT INTO commerce_phones(account_id,phone,shared) VALUES(?,?,?) ON CONFLICT(account_id) DO UPDATE SET phone=excluded.phone,shared=excluded.shared',(a['id'],phone,int(p['shared'])))
            c.execute('INSERT INTO commerce_preferences VALUES(?,?,?) ON CONFLICT(account_id) DO UPDATE SET marketing=excluded.marketing,personalization=excluded.personalization',(a['id'],int(p.get('marketing',False)),int(p.get('personalization',False))))
            # Sharing a number is explicit and only affects already linked shops.
            if p['shared']:
                for m in c.execute('SELECT a.id,a.shop_id FROM wallet_cards w JOIN crm_customers a ON a.id=w.customer_id WHERE w.account_id=? AND w.card_hash=a.code_hash',(a['id'],)).fetchall():
                    collision=c.execute('SELECT 1 FROM crm_customers WHERE shop_id=? AND phone_normalized=? AND id<>?',(m['shop_id'],phone,m['id'])).fetchone()
                    if not collision:c.execute('UPDATE crm_customers SET phone=?,phone_normalized=? WHERE id=?',(phone,phone,m['id']))
            else:
                c.execute("UPDATE crm_customers SET phone='',phone_normalized=NULL WHERE id IN (SELECT customer_id FROM wallet_cards WHERE account_id=?)",(a['id'],))
        return jsonify(ok=True,verified=False,message='Numéro enregistré, non vérifié. Il ne permet pas de se connecter au compte.')

    @app.post('/api/commerce/join')
    def commerce_join():
        p=payload();sid=p.get('shop_id');invite=p.get('invite')
        if type(sid)is not int or p.get('consent')is not True:return err('Votre accord est requis')
        if not throttle('commerce_join',request.remote_addr or 'local',30):return err('Réessayez plus tard',429)
        with db() as c:
            c.execute('BEGIN IMMEDIATE');a=account(c)
            if not a:return err('Connexion requise',401)
            if not a['email_verified']:return err('Confirmez votre email avant de rejoindre un commerce',403)
            if not is_active(c,sid):return err('Commerce indisponible',404)
            m=member(c,a['id'],sid)
            if m:return jsonify(ok=True,id=m['id'],duplicate=True)
            number=c.execute('SELECT phone FROM commerce_phones WHERE account_id=? AND shared=1',(a['id'],)).fetchone()
            if not number:return err('Ajoutez votre téléphone et autorisez son partage dans votre profil',409)
            number=number[0]
            if invite:
                if not isinstance(invite,str) or len(invite)>100:return err('Invitation invalide')
                inv=c.execute('SELECT * FROM commerce_invites WHERE digest=? AND shop_id=? AND used IS NULL AND expires>?',(digest(invite),sid,int(time.time()))).fetchone()
                if not inv:return err('Invitation expirée ou déjà utilisée',409)
                m=c.execute('SELECT * FROM crm_customers WHERE id=? AND shop_id=?',(inv['customer_id'],sid)).fetchone()
                if not m or m['phone_normalized']!=number:return err('Invitation et numéro incompatibles',409)
                if c.execute('SELECT 1 FROM wallet_cards WHERE customer_id=?',(m['id'],)).fetchone():return err('Carte déjà associée',409)
                cid,h=m['id'],m['code_hash']
                c.execute('UPDATE commerce_invites SET used=?,account_id=? WHERE digest=?',(int(time.time()),a['id'],digest(invite)))
            else:
                if c.execute('SELECT 1 FROM crm_customers WHERE shop_id=? AND phone_normalized=?',(sid,number)).fetchone():return err('Ce commerce possède déjà une fiche pour ce numéro. Demandez-lui une invitation personnelle.',409)
                h=digest(secrets.token_urlsafe(32))
                cid=c.execute('INSERT INTO crm_customers(shop_id,name,phone,phone_normalized,code_hash,consent) VALUES(?,?,?,?,?,?)',(sid,a['name'],number,number,h,int(p.get('marketing')is True))).lastrowid
            c.execute('INSERT INTO wallet_cards VALUES(?,?,?)',(cid,a['id'],h))
            c.execute('INSERT INTO store_memberships VALUES(?,?,?,?)',(a['id'],sid,cid,h))
            audit(c,sid,'membership_approved',cid)
        return jsonify(ok=True,id=cid),201

    @app.post('/api/commerce/customer/search')
    def commerce_search():
        sid=merchant()
        if not throttle('commerce_phone_search',str(sid),40):return err('Trop de recherches. Réessayez plus tard.',429)
        try:phone=phone_number(payload().get('phone'))
        except ValueError as e:return err(str(e))
        with db() as c:
            rows=[dict(r) for r in c.execute('SELECT id,name,phone,created FROM crm_customers WHERE shop_id=? AND phone_normalized=? LIMIT 10',(sid,phone))]
            for r in rows:r.update(points=balance(c,r['id']),phone_verified=False)
            audit(c,sid,'customer_search')  # No raw number in audit or Analytics.
        return jsonify(customers=rows,ambiguous=len(rows)>1)

    @app.post('/api/commerce/customer/invite')
    def commerce_invite():
        sid=merchant();cid=payload().get('id')
        if type(cid)is not int:return err('Client invalide')
        token=secrets.token_urlsafe(32)
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            r=c.execute('SELECT * FROM crm_customers WHERE id=? AND shop_id=?',(cid,sid)).fetchone()
            if not r or not r['phone_normalized']:return err('Fiche avec numéro valide requise',404)
            if c.execute('SELECT 1 FROM wallet_cards WHERE customer_id=?',(cid,)).fetchone():return err('Cette carte est déjà rattachée',409)
            c.execute('DELETE FROM commerce_invites WHERE customer_id=? OR expires<=?',(cid,int(time.time())))
            c.execute('INSERT INTO commerce_invites(digest,shop_id,customer_id,expires) VALUES(?,?,?,?)',(digest(token),sid,cid,int(time.time())+600))
            audit(c,sid,'invitation_created',cid)
        return jsonify(invite=token,expires_in=600)

    @app.post('/api/commerce/points')
    def commerce_points():
        sid=merchant();p=payload();cid=p.get('id');pts=p.get('points');label=clean(p.get('reason'),200);key=p.get('key')
        if type(cid)is not int or type(pts)is not int or not -100000<=pts<=100000 or not pts or not isinstance(key,str) or not re.fullmatch('[A-Za-z0-9_-]{16,80}',key) or not label:
            return err('Client, points entiers, motif et référence requis')
        key='commerce:'+str(sid)+':'+key
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            if not c.execute('SELECT 1 FROM crm_customers WHERE id=? AND shop_id=?',(cid,sid)).fetchone():return err('Client introuvable',404)
            old=c.execute('SELECT customer_id,points,label FROM loyalty_ledger WHERE request_key=?',(key,)).fetchone()
            if old:
                if old['customer_id']==cid and old['points']==pts and old['label']==label:return jsonify(ok=True,duplicate=True)
                return err('Référence déjà utilisée',409)
            if balance(c,cid)+pts<0:return err('Solde insuffisant',409)
            c.execute("INSERT INTO loyalty_ledger(customer_id,kind,points,label,request_key) VALUES(?,'manual',?,?,?)",(cid,pts,label,key))
            audit(c,sid,'points_adjusted',cid,points=pts,reason=label)
        return jsonify(ok=True,points=pts),201

    @app.post('/api/commerce/reward')
    def commerce_reward():
        sid=merchant();p=payload();ident=p.get('id');title=clean(p.get('title'),100);cost=p.get('cost');photo=p.get('photo');active=p.get('active',True)
        if not title or type(cost)is not int or not 1<=cost<=100000 or type(active)is not bool or ident is not None and type(ident)is not int:return err('Avantage invalide')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            if not owned(c,sid,photo):return err('Photo invalide')
            values=(title,cost,clean(p.get('description'),240),clean(p.get('conditions'),500),photo,int(active))
            if ident is None:ident=c.execute('INSERT INTO rewards(title,cost,description,conditions,photo,active,shop_id) VALUES(?,?,?,?,?,?,?)',(*values,sid)).lastrowid
            elif not c.execute('UPDATE rewards SET title=?,cost=?,description=?,conditions=?,photo=?,active=? WHERE id=? AND shop_id=?',(*values,ident,sid)).rowcount:return err('Avantage introuvable',404)
            audit(c,sid,'reward_saved',ident)
        return jsonify(ok=True,id=ident),201 if p.get('id')is None else 200

    @app.get('/api/commerce/business')
    def commerce_business():
        sid=merchant();period=request.args.get('period','month');now=today()
        start={'day':now,'week':now-timedelta(days=now.weekday()),'month':now.replace(day=1),'year':now.replace(month=1,day=1)}.get(period)
        if start is None:return err('Période invalide')
        with db() as c:
            customers=[dict(r) for r in c.execute('''SELECT a.id,a.name,a.phone,a.created,COALESCE(SUM(l.points),0) points,MAX(l.created) last_activity FROM crm_customers a
              LEFT JOIN loyalty_ledger l ON l.customer_id=a.id WHERE a.shop_id=? GROUP BY a.id ORDER BY a.id DESC LIMIT 500''',(sid,))]
            daily=[dict(r) for r in c.execute('''SELECT date(l.created,'+1 hour') day,COUNT(*) activities,SUM(CASE WHEN l.points>0 THEN l.points ELSE 0 END) points FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id
              WHERE a.shop_id=? AND date(l.created,'+1 hour') BETWEEN ? AND ? GROUP BY day ORDER BY day''',(sid,str(start),str(now)))]
            stats=dict(c.execute('''SELECT COUNT(DISTINCT a.id) active_customers,COALESCE(SUM(CASE WHEN l.points>0 THEN l.points ELSE 0 END),0) points_issued,
              COUNT(CASE WHEN l.kind IN ('redeem','discount','code') THEN 1 END) advantages FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id
              WHERE a.shop_id=? AND date(l.created,'+1 hour') BETWEEN ? AND ?''',(sid,str(start),str(now))).fetchone())
            stats.update(customers=c.execute('SELECT COUNT(*) FROM crm_customers WHERE shop_id=?',(sid,)).fetchone()[0],new_customers=c.execute("SELECT COUNT(*) FROM crm_customers WHERE shop_id=? AND date(created,'+1 hour') BETWEEN ? AND ?",(sid,str(start),str(now))).fetchone()[0],repeat_customers=c.execute("SELECT COUNT(*) FROM (SELECT l.customer_id FROM loyalty_ledger l JOIN crm_customers a ON a.id=l.customer_id WHERE a.shop_id=? AND date(l.created,'+1 hour') BETWEEN ? AND ? GROUP BY l.customer_id HAVING COUNT(*)>1)",(sid,str(start),str(now))).fetchone()[0],coupons_used=c.execute("SELECT COUNT(*) FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE o.shop_id=? AND date(q.used,'unixepoch','+1 hour') BETWEEN ? AND ?",(sid,str(start),str(now))).fetchone()[0],storefront_views=None)
            promotions=offers(c,sid,public=False);stats['active_promotions']=sum(o['status']=='active' for o in promotions)
            return jsonify(profile=profile(c,sid),customers=customers,promotions=promotions,rewards=[dict(r) for r in c.execute('SELECT * FROM rewards WHERE shop_id=? ORDER BY cost',(sid,))],stats=stats,daily=daily,period=period,timezone='Africa/Tunis',activities=[dict(r) for r in c.execute('SELECT action,object_id,details,created FROM commerce_audit WHERE shop_id=? ORDER BY id DESC LIMIT 100',(sid,))])

    @app.post('/api/commerce/promotion')
    def commerce_promotion(data=None):
        sid=merchant();p=payload() if data is None else data;title=clean(p.get('title'),100);desc=clean(p.get('description'),1000);start=p.get('starts');end=p.get('ends');benefit=p.get('benefit','advantage');audience=p.get('audience','public');state=p.get('state','active');disc=p.get('discount');max_uses=p.get('max_uses');ident=p.get('id');photo=p.get('photo')
        try:
            if date.fromisoformat(start).isoformat()!=start or date.fromisoformat(end).isoformat()!=end or start>end or (date.fromisoformat(end)-date.fromisoformat(start)).days>366:raise ValueError()
        except (ValueError,TypeError):return err('Dates invalides (maximum un an)')
        if not title or not desc or benefit not in ('discount','gift','bogo','advantage') or audience not in ('public','members','vip','inactive') or state not in ('draft','active','suspended','archived') or any(k in p for k in ('sponsored','priority')):return err('Promotion invalide')
        if benefit=='discount' and (type(disc)is not int or not 1<=disc<=100):return err('Réduction entre 1 et 100 % requise')
        if max_uses is not None and (type(max_uses)is not int or not 1<=max_uses<=1000000):return err('Limite invalide')
        if ident is not None and type(ident)is not int:return err('Promotion invalide')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            if not owned(c,sid,photo):return err('Photo invalide')
            values=('coupon' if benefit=='discount' else 'promotion',title,desc,start,end,disc if benefit=='discount' else None,photo,audience,benefit,clean(p.get('conditions'),500),state,int(state=='active'),max_uses)
            if ident is not None:
                old=c.execute('SELECT * FROM storefront_offers WHERE id=? AND shop_id=?',(ident,sid)).fetchone()
                if not old:return err('Promotion introuvable',404)
                if c.execute('SELECT 1 FROM storefront_coupons WHERE offer_id=?',(ident,)).fetchone() and any(old[k]!=v for k,v in [('title',title),('description',desc),('starts',start),('ends',end),('discount',values[5]),('audience',audience),('benefit',benefit),('conditions',values[9]),('max_uses',max_uses)]):return err('Des coupons existent : créez une nouvelle promotion pour changer ses conditions',409)
                c.execute('UPDATE storefront_offers SET kind=?,title=?,description=?,starts=?,ends=?,discount=?,photo=?,audience=?,benefit=?,conditions=?,state=?,active=?,max_uses=?,old_price=NULL,new_price=NULL WHERE id=? AND shop_id=?',(*values,ident,sid))
            else:
                if c.execute('SELECT COUNT(*) FROM storefront_offers WHERE shop_id=?',(sid,)).fetchone()[0]>=500:return err('Limite de promotions atteinte',409)
                ident=c.execute('INSERT INTO storefront_offers(kind,title,description,starts,ends,discount,photo,audience,benefit,conditions,state,active,max_uses,shop_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(*values,sid)).lastrowid
            # Keep any old Nearby ID pointing to the canonical record, without duplication.
            c.execute('UPDATE nearby_offers SET title=?,description=?,starts=?,ends=?,active=? WHERE promotion_id=?',(title,desc,start,end,int(state=='active'),ident))
            audit(c,sid,'promotion_saved',ident,state=state)
        return jsonify(ok=True,id=ident),200 if p.get('id') is not None else 201

    @app.post('/api/commerce/nearby')
    def commerce_nearby():
        sid=merchant();p=payload();ident=p.get('id');enabled=p.get('enabled');radius=p.get('radius')
        if type(ident)is not int or type(enabled)is not bool or type(radius)is not int or radius<100:return err('Promotion, activation et rayon requis')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            maximum=c.execute('SELECT radius FROM subscriptions WHERE shop_id=?',(sid,)).fetchone()[0]
            if radius>maximum:return err('Ce rayon dépasse votre abonnement')
            if not c.execute('SELECT 1 FROM nearby_locations WHERE shop_id=? AND location_confirmed=1',(sid,)).fetchone():return err('Confirmez la localisation de votre établissement')
            o=c.execute('SELECT * FROM storefront_offers WHERE id=? AND shop_id=?',(ident,sid)).fetchone()
            if not o:return err('Promotion introuvable',404)
            if enabled and o['audience']!='public':return err('Nearby diffuse uniquement les promotions publiques')
            c.execute('UPDATE storefront_offers SET nearby_enabled=?,radius=? WHERE id=?',(int(enabled),radius,ident))
            audit(c,sid,'nearby_changed',ident,enabled=enabled,radius=radius)
        return jsonify(ok=True)

    @app.post('/api/commerce/storefront')
    def commerce_storefront():
        sid=merchant();p=payload()
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            old=profile(c,sid)
            vals={k:p.get(k,old.get(k)) for k in ('photo','cover','logo','description','hours','phone','website','social')}
            if any(not owned(c,sid,vals[k]) for k in ('photo','cover','logo')):return err('Photo invalide')
            for k,n in [('description',1000),('hours',700),('phone',40),('website',300),('social',500)]:
                if vals[k] is None:vals[k]=''
                if not isinstance(vals[k],str) or len(vals[k])>n:return err('Champ invalide : '+k)
            if vals['website'] and not re.fullmatch(r'https://[^\s<>"\x27]+',vals['website']):return err('Lien HTTPS requis')
            if p.get('published') is not None:
                if type(p['published'])is not bool:return err('Publication invalide')
                current={**old,**vals}
                missing=[k for k in ('name','city','category','address','photo','phone') if not current.get(k)]
                if p['published'] and missing:return err('Complétez : '+', '.join(missing))
            c.execute('INSERT INTO storefront_profiles(shop_id) VALUES(?) ON CONFLICT DO NOTHING',(sid,))
            c.execute('UPDATE storefront_profiles SET '+','.join(k+'=?' for k in vals)+' WHERE shop_id=?',(*vals.values(),sid))
            if p.get('published') is not None:
                c.execute('UPDATE storefront_profiles SET published=? WHERE shop_id=?',(int(p['published']),sid))
            audit(c,sid,'storefront_saved')
        return jsonify(ok=True)

    @app.post('/api/commerce/code')
    def commerce_code():
        sid=merchant();p=payload();cid=p.get('customer_id');disc=p.get('discount');title=clean(p.get('title'),100);expires=p.get('expires');uses=p.get('max_uses',1)
        try:
            if date.fromisoformat(expires)<today():raise ValueError()
        except (ValueError,TypeError):return err('Expiration invalide')
        if not title or type(disc)is not int or not 1<=disc<=100 or type(uses)is not int or not 1<=uses<=10000 or cid is not None and type(cid)is not int:return err('Code invalide')
        code='TB-'+secrets.token_hex(8).upper()
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            if cid is not None and not c.execute('SELECT 1 FROM crm_customers WHERE id=? AND shop_id=?',(cid,sid)).fetchone():return err('Client introuvable',404)
            ident=c.execute('INSERT INTO commerce_codes(shop_id,digest,title,discount,expires,max_uses,customer_id) VALUES(?,?,?,?,?,?,?)',(sid,digest(code),title,disc,expires,uses,cid)).lastrowid
            audit(c,sid,'promotion_code_created',ident)
        return jsonify(code=code,id=ident),201

    @app.post('/api/commerce/code/use')
    def commerce_code_use():
        p=payload();code=p.get('code');sid=p.get('shop_id')
        if not isinstance(code,str) or not re.fullmatch(r'TB-[A-F0-9]{16}',code) or type(sid)is not int:return err('Code invalide')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');a=account(c)
            if not a:return err('Connexion requise',401)
            if not is_active(c,sid):return err('Commerce indisponible',404)
            r=c.execute('SELECT * FROM commerce_codes WHERE digest=? AND shop_id=? AND active=1 AND expires>=?',(digest(code),sid,str(today()))).fetchone()
            if not r:return err('Code inconnu ou expiré dans cet établissement',404)
            m=member(c,a['id'],sid)
            if not m or r['customer_id']is not None and r['customer_id']!=m['id']:return err('Code réservé à un autre client',403)
            if c.execute('SELECT 1 FROM commerce_code_uses WHERE code_id=? AND account_id=?',(r['id'],a['id'])).fetchone():return err('Code déjà utilisé',409)
            if c.execute('SELECT COUNT(*) FROM commerce_code_uses WHERE code_id=?',(r['id'],)).fetchone()[0]>=r['max_uses']:return err('Code épuisé',409)
            c.execute('INSERT INTO commerce_code_uses(code_id,account_id) VALUES(?,?)',(r['id'],a['id']))
            # Issue a single-use coupon rather than trusting a reusable screen.
            oid=c.execute("INSERT INTO storefront_offers(shop_id,kind,title,description,starts,ends,discount,audience,benefit) VALUES(?,'coupon',?,'Avantage personnel',?,?,?,'personal','discount')",(sid,r['title'],str(today()),r['expires'],r['discount'])).lastrowid
            coupon='TN-'+secrets.token_hex(6).upper()
            c.execute('INSERT INTO storefront_coupons(code,offer_id,account_id) VALUES(?,?,?)',(coupon,oid,a['id']))
            audit(c,sid,'promotion_code_used',r['id'])
            notify(c,m['id'],'Votre coupon est disponible',r['title'])
        return jsonify(ok=True,code=coupon,title=r['title'],discount=r['discount']),201

    @app.get('/api/commerce/admin')
    def commerce_admin():
        with db() as c:
            admin(c)
            return jsonify(sponsors=[dict(r) for r in c.execute('SELECT b.*,s.name shop FROM commerce_sponsors b JOIN shops s ON s.id=b.shop_id ORDER BY b.priority DESC,b.id DESC')],shops=[dict(r) for r in c.execute('SELECT s.id,s.name,s.city,t.status,t.category FROM shops s JOIN subscriptions t ON t.shop_id=s.id ORDER BY s.name')],stats=dict(c.execute('SELECT (SELECT COUNT(*) FROM shops) shops,(SELECT COUNT(*) FROM consumer_accounts) consumers,(SELECT COUNT(*) FROM storefront_offers) promotions').fetchone()),operations=[dict(r) for r in c.execute('SELECT id,action,created FROM admin_operations ORDER BY id DESC LIMIT 50')])

    @app.post('/api/commerce/sponsor')
    def commerce_sponsor():
        p=payload()
        with db() as c:
            c.execute('BEGIN IMMEDIATE');admin(c)
            sid=p.get('shop_id');ident=p.get('id');title=clean(p.get('title'),100);desc=clean(p.get('description'),500);state=p.get('status','draft');priority=p.get('priority',0);photo=p.get('photo');start=p.get('starts');end=p.get('ends')
            if type(sid)is not int or not title or not desc or state not in ('draft','active','suspended','archived') or type(priority)is not int or not -1000<=priority<=1000 or ident is not None and type(ident)is not int:return err('Bannière invalide')
            try:
                if date.fromisoformat(start)>date.fromisoformat(end):raise ValueError()
            except (ValueError,TypeError):return err('Dates invalides')
            if not is_active(c,sid) or not owned(c,sid,photo):return err('Commerce ou photo invalide')
            if state=='active' and (profile(c,sid)['missing'] or not profile(c,sid)['published']):return err('Publiez d’abord une vitrine complète')
            values=(sid,title,desc,photo,start,end,clean(p.get('cta'),40)or'Découvrir',priority,state)
            if ident is None:ident=c.execute('INSERT INTO commerce_sponsors(shop_id,title,description,photo,starts,ends,cta,priority,status) VALUES(?,?,?,?,?,?,?,?,?)',values).lastrowid
            elif not c.execute('UPDATE commerce_sponsors SET shop_id=?,title=?,description=?,photo=?,starts=?,ends=?,cta=?,priority=?,status=? WHERE id=?',(*values,ident)).rowcount:return err('Bannière introuvable',404)
            c.execute('INSERT INTO admin_operations(shop_id,action,details) VALUES(?,?,?)',(sid,'sponsor_saved',json.dumps({'id':ident,'status':state})))
        return jsonify(ok=True,id=ident)

    @app.post('/api/commerce/sponsor/photo')
    def commerce_sponsor_photo():
        import base64,binascii,io
        from PIL import Image,ImageOps
        p=payload();sid=p.get('shop_id');raw=p.get('image')
        with db() as c:
            admin(c)
            if type(sid)is not int or not is_active(c,sid):return err('Commerce invalide')
        if not isinstance(raw,str) or len(raw)>350000:return err('Image trop volumineuse',413)
        try:
            with Image.open(io.BytesIO(base64.b64decode(raw,validate=True))) as im:
                if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>16000000:raise ValueError()
                im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1000,1000));out=io.BytesIO();im.save(out,'JPEG',quality=78,optimize=True)
                if out.tell()>180000:raise ValueError()
        except (ValueError,TypeError,OSError,binascii.Error,Image.DecompressionBombError):return err('Image JPEG, PNG ou WebP valide requise')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');admin(c)
            if c.execute('SELECT COUNT(*) FROM storefront_photos WHERE shop_id=?',(sid,)).fetchone()[0]>=30:return err('Limite de 30 photos atteinte',409)
            ident=secrets.token_hex(16);c.execute('INSERT INTO storefront_photos VALUES(?,?,?)',(ident,sid,out.getvalue()))
        return jsonify(id=ident),201

    # Apply privacy and audience rules to older APK routes too.
    original_detail=app.view_functions['sf_store']
    def store_detail(sid):
        with db() as c:
            p=profile(c,sid);a=account(c);aid=a['id'] if a else None
            if not p or not is_active(c,sid) or not p['published'] or p['missing']:return err('Commerce indisponible',404)
        response=original_detail(sid)
        if isinstance(response,tuple):return response
        d=response.get_json()
        with db() as c:
            d.update(photo=p['photo'],cover=p['cover']or p['photo'],phone=p['phone'],website=p['website'],social=p['social'],offers=offers(c,sid,aid),nearby=[])
            m=member(c,aid,sid)
            d['history']=[dict(r) for r in c.execute('SELECT kind,points,label,created FROM loyalty_ledger WHERE customer_id=? ORDER BY id DESC LIMIT 100',(m['id'],))] if m else []
            d['joined']=bool(m)
            # Personal code coupons remain visible to their owner even after opt-out.
            d['coupons']=[dict(r) for r in c.execute('SELECT q.offer_id,q.code,q.used,o.title,o.discount FROM storefront_coupons q JOIN storefront_offers o ON o.id=q.offer_id WHERE q.account_id=? AND o.shop_id=? AND o.active=1 AND o.starts<=? AND o.ends>=?',(aid,sid,str(today()),str(today())))] if aid else []
        return jsonify(d)
    app.view_functions['sf_store']=store_detail
    def store_directory():
        with db() as c:
            a=account(c)
            return jsonify(stores=directory(c,a['id'] if a else None))
    app.view_functions['sf_directory']=store_directory

    @app.before_request
    def commerce_guards():
        if request.method=='POST' and request.path=='/api/storefront/coupon/claim':
            with db() as c:
                a=account(c);o=c.execute('SELECT * FROM storefront_offers WHERE id=?',(payload().get('id'),)).fetchone()
                if a and o:
                    if not visible(c,o,a['id']):return err('Coupon indisponible',404)
                    if o['max_uses']is not None and not c.execute('SELECT 1 FROM storefront_coupons WHERE offer_id=? AND account_id=?',(o['id'],a['id'])).fetchone() and c.execute('SELECT COUNT(*) FROM storefront_coupons WHERE offer_id=?',(o['id'],)).fetchone()[0]>=o['max_uses']:return err('Tous les coupons sont attribués',409)
        # Rate limits apply to legacy and new sensitive actions.
        if request.method=='POST' and request.path.startswith('/api/commerce/') and not throttle('commerce_write',request.remote_addr or 'local',200):return err('Trop de demandes',429)

    def nearby_public():
        with db() as c:
            a=account(c);aid=a['id'] if a else None;items=[]
            for o in offers(c,aid=aid):
                if not o['nearby_enabled'] or o['audience']!='public':continue
                loc=c.execute('SELECT * FROM nearby_locations WHERE shop_id=? AND location_confirmed=1',(o['shop_id'],)).fetchone()
                p=profile(c,o['shop_id'])
                if not loc or not p['published'] or p['missing']:continue
                maximum=c.execute('SELECT radius FROM subscriptions WHERE shop_id=?',(o['shop_id'],)).fetchone()[0]
                legacy=c.execute('SELECT id,category FROM nearby_offers WHERE promotion_id=?',(o['id'],)).fetchone()
                items.append({**o,'id':legacy['id'] if legacy else o['id'],'promotion_id':o['id'],'shop':p['name'],'category':legacy['category'] if legacy else p['category'],'lat':loc['lat'],'lon':loc['lon'],'address':loc['address'],'radius':min(o['radius'] or maximum,maximum)})
            return jsonify(offers=items)
    app.view_functions['nearby']=nearby_public

    def customer_create():
        sid=merchant();p=payload();name=clean(p.get('name'));code=secrets.token_urlsafe(24)
        try:number=phone_number(p.get('phone')) if p.get('phone') else None
        except ValueError as e:return err(str(e))
        if not name:return err('Nom requis')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            if c.execute('SELECT 1 FROM crm_customers WHERE shop_id=? AND phone_normalized=?',(sid,number)).fetchone():return err('Ce numéro existe déjà chez vous. Recherchez le client.',409)
            cid=c.execute('INSERT INTO crm_customers(shop_id,name,phone,phone_normalized,consent,code_hash) VALUES(?,?,?,?,?,?)',(sid,name,number or '',number,int(p.get('consent')is True),digest(code))).lastrowid
            audit(c,sid,'customer_created',cid)
        return jsonify(id=cid,code=code,phone_verified=False),201
    app.view_functions['customer_create']=customer_create

    # Legacy writes also enter the same table. Old records remain intact for rollback.
    old_offer_save=app.view_functions['sf_save_offer']
    old_campaign_save=app.view_functions['campaign']
    old_nearby_save=app.view_functions['nearby_offer']
    def sync_legacy(source,source_id):
        with db() as c:
            r=c.execute('SELECT * FROM '+source+' WHERE id=?',(source_id,)).fetchone()
            public=source=='nearby_offers'
            oid=c.execute('''INSERT INTO storefront_offers(shop_id,kind,title,description,starts,ends,active,audience,benefit,state,nearby_enabled,visual)
                VALUES(?,'promotion',?,?,?,?,?,?,'advantage',?,?,?)''',(r['shop_id'],r['title'],r['description'],r['starts'],r['ends'],r['active'],'public' if public else ('members' if r['segment']=='all' else r['segment']),'active' if r['active'] else 'suspended',int(public),'general' if public else r['visual'])).lastrowid
            c.execute('INSERT INTO commerce_imports VALUES(?,?,?)',(source,source_id,oid))
            if public:c.execute('UPDATE nearby_offers SET promotion_id=? WHERE id=?',(oid,source_id))

    def legacy_promotion():
        p=payload()
        if 'sponsored' in p:return err('Administration requise',403)
        if 'old_price' in p and p.get('kind')!='coupon':return old_offer_save()
        benefit=p.get('benefit') or ('discount' if p.get('kind')=='coupon' or p.get('discount') else 'advantage')
        return commerce_promotion({**p,'benefit':benefit,'audience':p.get('audience','public')})
    app.view_functions['sf_save_offer']=legacy_promotion
    def legacy_campaign():
        response=old_campaign_save()
        if isinstance(response,tuple) and response[1]==201:sync_legacy('campaigns',response[0].get_json()['id'])
        return response
    app.view_functions['campaign']=legacy_campaign
    def legacy_nearby():
        response=old_nearby_save()
        if isinstance(response,tuple) and response[1]==201:sync_legacy('nearby_offers',response[0].get_json()['id'])
        return response
    app.view_functions['nearby_offer']=legacy_nearby
    def legacy_stop():
        sid=merchant();ident=payload().get('id')
        if type(ident)is not int:return err('Promotion invalide')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');merchant(c)
            source={'stop':'campaigns','nearby_stop':'nearby_offers'}.get(request.endpoint)
            if source:
                alias=c.execute('SELECT offer_id FROM commerce_imports WHERE source=? AND source_id=?',(source,ident)).fetchone()
                if not alias:return err('Promotion introuvable',404)
                c.execute('UPDATE '+source+' SET active=0 WHERE id=? AND shop_id=?',(ident,sid))
                ident=alias[0]
            if not c.execute("UPDATE storefront_offers SET active=0,state='suspended' WHERE id=? AND shop_id=?",(ident,sid)).rowcount:return err('Promotion introuvable',404)
            audit(c,sid,'promotion_suspended',ident)
        return jsonify(ok=True)
    for endpoint in ('stop','nearby_stop','sf_stop'):app.view_functions[endpoint]=legacy_stop

    def claim():
        ident=payload().get('id')
        if type(ident)is not int:return err('Coupon invalide')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');a=account(c)
            if not a:return err('Connexion requise',401)
            o=c.execute('SELECT * FROM storefront_offers WHERE id=?',(ident,)).fetchone()
            if not o or not is_active(c,o['shop_id']) or o['kind']!='coupon' or not visible(c,o,a['id']):return err('Coupon indisponible',404)
            storefront=profile(c,o['shop_id'])
            if not storefront['published'] or storefront['missing']:return err('Coupon indisponible',404)
            old=c.execute('SELECT code,used FROM storefront_coupons WHERE offer_id=? AND account_id=?',(ident,a['id'])).fetchone()
            if old:return jsonify(**dict(old),duplicate=True)
            if o['max_uses']is not None and c.execute('SELECT COUNT(*) FROM storefront_coupons WHERE offer_id=?',(ident,)).fetchone()[0]>=o['max_uses']:return err('Tous les coupons sont attribués',409)
            code='TN-'+secrets.token_hex(6).upper()
            c.execute('INSERT INTO storefront_coupons(code,offer_id,account_id) VALUES(?,?,?)',(code,ident,a['id']))
        return jsonify(code=code,used=None),201
    app.view_functions['sf_claim']=claim

    original_card=app.view_functions['card']
    def loyalty_card():
        response=original_card()
        if isinstance(response,tuple):return response
        with db() as c:
            a=account(c)
            r=c.execute('SELECT shop_id FROM crm_customers WHERE id=? AND code_hash=?',(session.get('card'),session.get('card_hash'))).fetchone()
            d=response.get_json()
            if r and a:d['campaigns']=offers(c,r[0],a['id'])
        return jsonify(d)
    app.view_functions['card']=loyalty_card

    # Primary photos and sponsored banners use the existing protected media store.
    original_media=app.view_functions['sf_media']
    def media(ident):
        if not re.fullmatch('[a-f0-9]{32}',ident):return err('Photo introuvable',404)
        with db() as c:
            row=c.execute('''SELECT x.image,x.shop_id FROM storefront_photos x WHERE x.id=? AND NOT EXISTS(SELECT 1 FROM storefront_hidden_photos h WHERE h.photo_id=x.id)
              AND (EXISTS(SELECT 1 FROM storefront_profiles p WHERE (p.photo=x.id OR p.logo=x.id) AND p.published=1)
              OR EXISTS(SELECT 1 FROM commerce_sponsors b WHERE b.photo=x.id AND b.status='active' AND b.starts<=? AND b.ends>=?))''',(ident,str(today()),str(today()))).fetchone()
            if row and is_active(c,row['shop_id']):
                import io
                from flask import send_file
                result=send_file(io.BytesIO(row['image']),mimetype='image/jpeg',max_age=0)
                result.headers['Cache-Control']='no-store'
                return result
        return original_media(ident)
    app.view_functions['sf_media']=media

    old_photo_delete=app.view_functions['sf_photo_delete']
    def photo_delete():
        sid=merchant();ident=payload().get('id')
        with db() as c:
            if c.execute('SELECT 1 FROM storefront_profiles WHERE shop_id=? AND (photo=? OR logo=?) UNION SELECT 1 FROM rewards WHERE shop_id=? AND photo=? UNION SELECT 1 FROM commerce_sponsors WHERE shop_id=? AND photo=?',(sid,ident,ident,sid,ident,sid,ident)).fetchone():return err('Photo utilisée : retirez-la de son emplacement avant de la supprimer',409)
        return old_photo_delete()
    app.view_functions['sf_photo_delete']=photo_delete

    original_wallet=app.view_functions['wallet_view']
    def wallet_view():
        response=original_wallet()
        if isinstance(response,tuple):return response
        d=response.get_json()
        with db() as c:
            for card in d['cards']:
                p=profile(c,card['shop_id'])
                card['photo']=p['photo'] if p else None
                nxt=c.execute('SELECT title,cost FROM rewards WHERE shop_id=? AND active=1 AND cost>? ORDER BY cost LIMIT 1',(card['shop_id'],card['points'])).fetchone()
                card['next_reward']=dict(nxt) if nxt else None
        return jsonify(d)
    app.view_functions['wallet_view']=wallet_view

    old_admin_change=app.view_functions['subscription_change']
    def admin_change():
        response=old_admin_change()
        if isinstance(response,tuple):return response
        if response.status_code==200:
            p=payload();sid=p.get('id');oid=p.get('offer_id')
            with db() as c:
                if p.get('action') in ('moderate_offer','offer_radius') and p.get('kind','nearby')=='nearby':
                    alias=c.execute('SELECT promotion_id FROM nearby_offers WHERE id=? AND shop_id=?',(oid,sid)).fetchone()
                    if alias and alias[0]:
                        if p['action']=='offer_radius':c.execute('UPDATE storefront_offers SET radius=? WHERE id=?',(p.get('radius'),alias[0]))
                        else:c.execute('UPDATE storefront_offers SET active=? WHERE id=?',(int(p['active']),alias[0]))
        return response
    app.view_functions['subscription_change']=admin_change

    @app.get('/client')
    @app.get('/business/v052')
    @app.get('/admin/v052')
    def commerce_page():return send_from_directory(app.static_folder,'commerce.html')

    @app.get('/admin/legacy')
    def commerce_legacy_admin():return send_from_directory(app.static_folder,'admin-cash.html')

    def business_page():return send_from_directory(app.static_folder,'commerce.html')
    for endpoint in ('crm_page','page','sf_merchant_page','wallet_page','sf_stores_page','admin_page'):
        app.view_functions[endpoint]=business_page
    old_nearby_page=app.view_functions['nearby_page']
    def nearby_page():return business_page() if request.path=='/nearby/business' else old_nearby_page()
    app.view_functions['nearby_page']=nearby_page
