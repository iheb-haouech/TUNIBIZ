import os,sys,tempfile,shutil,base64,io
from pathlib import Path
from werkzeug.security import generate_password_hash
from PIL import Image
import qrcode
P=Path(__file__).parent
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
 p=Path(tmp)
 for f in P.glob('*.py'):
  if not f.name.startswith('test_'):shutil.copy2(f,p/f.name)
 shutil.copytree(P/'static',p/'static')
 os.environ.update(TUNIBIZ_ENV='production',TUNIBIZ_SECRET='qa-'+('x'*64),TUNIBIZ_DATA_DIR=str(p/'data'),TUNIBIZ_ADMIN_PASSWORD_HASH=generate_password_hash('Test-admin-password'))
 sys.path.insert(0,str(p))
 from app import app,db
 from store_scan import BASE
 def get(a,path):return a.get(path,base_url='https://localhost')
 def post(a,path,body,status=200):
  r=a.post('/api'+path,json=body,headers={'X-CSRF-Token':get(a,'/api/session').json['csrf']},base_url='https://localhost')
  assert r.status_code==status,(path,r.status_code,r.json);return r.json
 admin=app.test_client();post(admin,'/admin/login',{'password':'Test-admin-password'})
 a=app.test_client()
 base={'name':'Type QA','city':'Test','address':'QA','lat':33.88,'lon':10.86,'confirmed':True,'email':'other@example.test','password':'Test-merchant-password','category':'other'}
 post(a,'/merchant/register',base,400)
 post(a,'/merchant/register',{**base,'category_detail':'Librairie'},201)
 with db() as c:
  sid=c.execute("SELECT shop_id FROM users WHERE email=?",(base['email'],)).fetchone()[0]
  slug=c.execute('SELECT slug FROM shops WHERE id=?',(sid,)).fetchone()[0]
 assert get(a,'/api/crm/store-qr').status_code==401
 assert get(a,'/join/'+slug).status_code==404
 post(admin,'/admin/shop',{'id':sid,'action':'cash','reference':'QA-receipt'})
 post(a,'/login',{'email':base['email'],'password':base['password']})
 qr=get(a,'/api/crm/store-qr').json
 assert qr['url']==BASE+'/join/'+slug
 assert get(a,'/join/'+slug).status_code==200
 im=Image.open(io.BytesIO(base64.b64decode(qr['png']))).convert('1')
 expected=qrcode.make(qr['url']).get_image().convert('1')
 assert im.size==expected.size and im.tobytes()==expected.tobytes()
 assert get(a,'/api/crm').json['dashboard']['shop']['category_detail']=='Librairie'
 assert get(admin,'/api/admin/shops').json['shops'][0]['category_detail']=='Librairie'
 public=get(a,'/static/tunibiz-download-qr.png')
 im=Image.open(io.BytesIO(public.data)).convert('1');expected=qrcode.make(BASE+'/download').get_image().convert('1')
 assert public.status_code==200 and im.tobytes()==expected.tobytes()
 assert b'tunibiz-download-qr.png' in get(a,'/').data and b'tunibiz-download-qr.png' in get(a,'/download').data
 # All new types; throttle budget leaves room for exactly these eight extra requests.
 for i,cat in enumerate(('grocery_general','drugstore','grocery','coffee','restaurant','bakery','shopping','clothing')):
  post(a,'/merchant/register',{**base,'email':f'type{i}@example.test','category':cat},201)
 post(admin,'/admin/shop',{'id':sid,'action':'block'})
 assert get(a,'/api/crm/store-qr').status_code==401 and get(a,'/join/'+slug).status_code==404
 print('PASS nine establishment types, mandatory other detail, activation-gated QR, matching PNG, public QR homepage and download, blocking')
