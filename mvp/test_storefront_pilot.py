"""Isolated storefront pilot: publication privacy, ownership, favorites and coupon terms."""
import os,sys,tempfile,shutil,io,base64
from pathlib import Path
from datetime import date,timedelta
from PIL import Image
from werkzeug.security import generate_password_hash
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_REQUIRE_EMAIL_VERIFICATION='0',TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+('x'*64),TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash('Test-admin-password'))
 sys.path.insert(0,str(p))
 from app import app,db
 ids={}
 with db() as c:
  for slug in ('first','second'):
   sid=c.execute('INSERT INTO shops(slug,name,city) VALUES(?,?,?)',(slug,slug,'Djerba')).lastrowid;ids[slug]=sid
   c.execute('INSERT INTO users(shop_id,email,password) VALUES(?,?,?)',(sid,slug+'@example.test',generate_password_hash('Test-merchant-password')))
   c.execute("INSERT INTO subscriptions(shop_id,status,paid_until,category) VALUES(?,'active','2099-01-01','drugstore')",(sid,))
   c.execute("INSERT INTO nearby_locations(shop_id,lat,lon,address,location_confirmed) VALUES(?,33.88,10.86,'Rue QA, Djerba',1)",(sid,))
 def get(a,path,status=200):
  r=a.get(path,base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:300]);return r
 def post(a,path,data,status=200):
  r=a.post('/api'+path,json=data,headers={'X-CSRF-Token':get(a,'/api/session').json['csrf']},base_url='https://localhost');assert r.status_code==status,(path,r.status_code,r.get_data(as_text=True)[:300]);return r.json
 m,n,a,b=[app.test_client() for _ in range(4)]
 for client,slug in ((m,'first'),(n,'second')):post(client,'/login',{'email':slug+'@example.test','password':'Test-merchant-password'})
 for client,email in ((a,'a'),(b,'b')):post(client,'/wallet/register',{'name':'QA '+email,'email':email+'@example.test','password':'Test-consumer-password'},201)
 im=Image.open(P/'static'/'media'/'boutique.webp').convert('RGB');im.thumbnail((480,480));buf=io.BytesIO();im.save(buf,'JPEG',quality=75);image=base64.b64encode(buf.getvalue()).decode()
 photo=post(m,'/storefront/photo',{'image':image},201)['id']
 foreign=post(n,'/storefront/photo',{'image':image},201)['id']
 private=post(m,'/storefront/photo',{'image':image},201)['id']
 get(a,'/media/store/'+photo,404)
 post(m,'/storefront/profile',{'description':'Une vraie vitrine','cover':None,'hours':'Lundi–samedi : 09:00–20:00','gallery':[photo]})
 d=get(a,'/api/stores/'+str(ids['first'])).json
 assert d['hours'].startswith('Lundi') and d['gallery']==[photo] and d['address']=='Rue QA, Djerba' and d['lat']==33.88
 assert d['points']==0 and get(a,'/media/store/'+photo).mimetype=='image/jpeg'
 get(a,'/media/store/'+private,404)
 post(m,'/storefront/photo/delete',{'id':photo},409)
 for value in ([foreign],[photo,photo],{'x':photo},[photo]*13):
  post(m,'/storefront/profile',{'description':'No','cover':None,'gallery':value},400)
 post(m,'/storefront/profile',{'description':'Updated','cover':None})
 assert get(a,'/api/stores/'+str(ids['first'])).json['hours']==d['hours']
 assert get(a,'/api/stores/'+str(ids['first'])).json['gallery']==[photo]
 post(m,'/storefront/profile',{'description':'No','cover':None,'hours':['bad']},400)
 post(m,'/stores/favorite',{'id':ids['first'],'favorite':1},400)
 post(app.test_client(),'/stores/favorite',{'id':ids['first'],'favorite':True},401)
 post(a,'/stores/favorite',{'id':ids['first'],'favorite':True})
 post(a,'/stores/favorite',{'id':ids['first'],'favorite':True})
 assert get(a,'/api/stores').json['stores'][0]['favorite'] is True
 assert get(b,'/api/stores').json['stores'][0]['favorite'] is False
 post(a,'/stores/favorite',{'id':ids['first'],'favorite':False})
 assert get(a,'/api/stores/'+str(ids['first'])).json['favorite'] is False
 post(a,'/wallet/store-scan',{'slug':'first'},201)
 with db() as c:
  c.execute("INSERT INTO rewards(shop_id,title,cost) VALUES(?,'Récompense QA',3)",(ids['first'],))
 assert get(a,'/api/stores/'+str(ids['first'])).json['points']==3
 assert get(b,'/api/stores/'+str(ids['first'])).json['points']==0
 assert get(a,'/api/stores/'+str(ids['second'])).json['points']==0
 today=date.today();base={'kind':'pack','title':'Pack QA','description':'Conditions QA','starts':today.isoformat(),'ends':(today+timedelta(days=10)).isoformat(),'old_price':20000,'new_price':15000,'photo':photo}
 pack=post(m,'/storefront/offer',base,201)['id']
 post(n,'/storefront/offer',{**base,'id':pack,'photo':None},404)
 post(m,'/storefront/offer',{**base,'id':True},400)
 post(m,'/storefront/offer',{**base,'id':pack,'new_price':10000})
 assert get(a,'/api/stores/'+str(ids['first'])).json['offers'][0]['reduction_percent']==50
 coupon=post(m,'/storefront/offer',{**base,'kind':'coupon','discount':10},201)['id']
 post(a,'/storefront/coupon/claim',{'id':coupon},201)
 post(m,'/storefront/offer',{**base,'id':coupon,'kind':'coupon','discount':90},409)
 post(m,'/storefront/offer',{**base,'id':coupon,'kind':'pack'},409)
 post(m,'/storefront/stop',{'id':pack})
 post(m,'/storefront/offer',{**base,'id':pack},409)
 with db() as c:c.execute('INSERT INTO storefront_hidden_photos VALUES(?,?)',(photo,ids['first']))
 assert get(a,'/api/stores/'+str(ids['first'])).json['gallery']==[]
 get(a,'/media/store/'+photo,404)
 assert get(a,'/api/stores/'+str(ids['first'])).json['offers'][0]['photo'] is None
 with db() as c:c.execute('DELETE FROM storefront_hidden_photos')
 post(m,'/storefront/profile',{'description':'Final','cover':None,'gallery':[]})
 post(m,'/storefront/photo/delete',{'id':private})
 with db() as c:c.execute("UPDATE subscriptions SET status='blocked' WHERE shop_id=?",(ids['first'],))
 post(a,'/stores/favorite',{'id':ids['first'],'favorite':True},404)
 post(m,'/storefront/profile',{'description':'blocked'},401)
 get(a,'/media/store/'+photo,404)
 print('PASS storefront pilot: hours, location, gallery privacy/ownership, moderated photos, isolated wallet balances, favorites, owned offer edits, server discounts, frozen claimed coupon terms and blocked shop')

 if '--browser' in sys.argv:
  from threading import Thread
  from werkzeug.serving import make_server
  from playwright.sync_api import sync_playwright
  with db() as c:
   c.execute("UPDATE subscriptions SET status='active' WHERE shop_id=?",(ids['first'],))
   c.execute("UPDATE storefront_profiles SET description=?,hours=? WHERE shop_id=?",('<img src=x onerror="window.xss=1">','Lundi–samedi : 09:00–20:00',ids['first']))
   c.execute('INSERT OR IGNORE INTO storefront_gallery VALUES(?,?,0)',(ids['first'],photo))
  app.config['SESSION_COOKIE_SECURE']=False
  server=make_server('127.0.0.1',0,app);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
  origin='http://127.0.0.1:'+str(server.server_port)
  errors=[]
  try:
   with sync_playwright() as playwright:
    try:browser=playwright.chromium.launch(headless=True)
    except Exception:browser=playwright.chromium.launch(channel='msedge',headless=True)
    customer=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1)
    customer.add_cookies([{'name':'session','value':a.get_cookie('session').value,'url':origin}])
    page=customer.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(origin+'/stores');page.wait_for_selector('#result-count')
    page.select_option('#category','drugstore');page.fill('#search-store','first')
    assert page.locator('#results .sf-card').count()==1
    page.click('[data-favorite]');page.wait_for_function("document.querySelector('[data-favorite]').getAttribute('aria-pressed')==='true'")
    page.click('#favorites');assert page.locator('#results .sf-card').count()==1
    page.click('#results .biz-link');page.wait_for_selector('#favorite-detail')
    assert page.locator('.sf-gallery img').count()==1
    assert page.locator('.sf-price').filter(has_text='3 points').count()==1
    assert page.evaluate('window.xss') is None
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    with db() as c:c.execute("UPDATE storefront_profiles SET description='Vitrine de démonstration — compte fictif de recette' WHERE shop_id=?",(ids['first'],))
    page.reload();page.wait_for_selector('#favorite-detail')
    out=Path('E:/TUNIBIZ-Dev/pilot050-storefront-390.png');page.screenshot(path=str(out),full_page=True)
    merchant=browser.new_context(viewport={'width':390,'height':844})
    merchant.add_cookies([{'name':'session','value':m.get_cookie('session').value,'url':origin}])
    mp=merchant.new_page();mp.on('pageerror',lambda error:errors.append(str(error)));mp.goto(origin+'/storefront');mp.wait_for_selector('#profile')
    assert mp.locator('[name="hours"]').input_value().startswith('Lundi')
    mp.fill('[name="hours"]','Tous les jours : 10:00–19:00')
    mp.locator('#profile button').click();mp.wait_for_function("document.querySelector('#storefront-status').textContent==='Vitrine enregistrée.'")
    assert mp.locator('[name="hours"]').input_value().startswith('Tous')
    mp.locator('[data-edit]').first.click()
    assert mp.locator('#offer-title').inner_text()=='Modifier cette offre'
    assert mp.locator('#cancel-edit').is_visible()
    mp.click('#cancel-edit')
    assert mp.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    mp.screenshot(path='E:/TUNIBIZ-Dev/pilot050-storefront-manager-390.png',full_page=True)
    assert errors==[],errors
    browser.close()
   print('PASS real Chromium 390px: category/search/favorites, gallery, wallet points, escaped XSS, hours save, edit form and no horizontal overflow; screenshots saved')
  finally:server.shutdown();thread.join(timeout=3)
